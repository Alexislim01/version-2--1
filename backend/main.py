from __future__ import annotations
import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pipeline.core import analyze

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
app = FastAPI(title='FireAtlas scientific API', version='1.0.0', description='Real FIRMS observations. Exploratory MODIS-equivalent calibration. Coverage is not cloud-free observing effort.')
from backend.final_api import router as final_router
app.include_router(final_router)


@lru_cache(maxsize=1)
def dataset() -> tuple[list[dict], list[dict]]:
    path = Path(os.getenv('FIREATLAS_DATA', str(ROOT/'data'/'sample.csv')))
    with path.open(newline='', encoding='utf-8-sig') as file:
        rows = list(csv.DictReader(file))
    metadata = json.loads((ROOT/'data'/'provenance.json').read_text())
    coverage = metadata['coverage']
    parquet = ROOT/'data'/'parquet'
    if parquet.exists() and list(parquet.glob('year=*/*.parquet')):
        import duckdb
        with duckdb.connect() as connection:
            result = connection.execute('SELECT * FROM read_parquet(?, union_by_name=true)', [str(parquet/'year=*'/'*.parquet')]).fetchdf()
        rows.extend(result.astype(object).where(result.notna(), None).to_dict('records'))
        for file in parquet.glob('*.coverage.json'):
            coverage.extend(json.loads(file.read_text()))
    return rows, coverage


PRESETS = {'borneo': [108, -5, 120, 8], 'malaysia': [99, .5, 120, 8], 'southeast-asia': [92, -11, 142, 28],
           'amazon': [-75, -20, -45, 6], 'california': [-125, 32, -114, 43], 'australia': [112, -44, 154, -10]}


@lru_cache(maxsize=32)
def query(aoi: str, start: str, end: str, sensors: str, confidence: int, grid: float, geometry: str | None) -> dict:
    try:
        bbox = PRESETS[aoi] if aoi in PRESETS else [float(n) for n in aoi.split(',')]
        if len(bbox) != 4:
            raise ValueError('AOI needs west,south,east,north or a supported preset.')
        selected = tuple(s.upper() for s in sensors.split(','))
        if not selected or any(s not in ('MODIS','VIIRS') for s in selected):
            raise ValueError('Sensors must be MODIS and/or VIIRS.')
        if not 30 <= confidence <= 100:
            raise ValueError('Confidence must be between 30 and 100.')
        shape = json.loads(geometry) if geometry else None
        if shape and shape.get('type') not in ('Polygon','MultiPolygon'):
            raise ValueError('Geometry must be Polygon or MultiPolygon.')
        rows, coverage = dataset()
        # Country archives do not establish coverage outside Malaysia. Custom imported
        # intervals carry their query bbox and are evaluated spatially below.
        regional = [c for c in coverage if (c.get('country') == 'Malaysia' and bbox[0] < 120 and bbox[2] > 99 and bbox[1] < 8 and bbox[3] > .5)
                    or ('bbox' in c and c['bbox'][0] <= bbox[0] and c['bbox'][1] <= bbox[1] and c['bbox'][2] >= bbox[2] and c['bbox'][3] >= bbox[3])]
        return analyze(rows, regional, start, end, bbox, grid, confidence, selected, shape)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def params(aoi: str = 'borneo', start: str = '2019-01-01', end: str = '2023-12-31',
           sensors: str = 'MODIS,VIIRS', confidence: int = 30, grid: float = .25, geometry: str | None = None) -> dict:
    return query(aoi, start, end, sensors, confidence, grid, geometry)


from fastapi import Depends


@app.get('/api/health')
def health() -> dict:
    rows, coverage = dataset()
    return {'status': 'ok', 'observations': len(rows), 'coverage': coverage}


@app.get('/api/dataset')
def browser_dataset() -> dict:
    """Validate/deduplicate, retaining native confidence for browser-side filters.

    Unknown confidence is retained as unknown and explicitly excluded by the UI.
    The analytical API and ingestion pipeline keep their existing cleaning defaults.
    """
    from pipeline.core import clean
    rows, coverage = dataset()
    metadata = json.loads((ROOT/'data'/'provenance.json').read_text())
    metadata['coverage'] = coverage
    return {'metadata': metadata, 'rows': [[r['latitude'], r['longitude'], r['acq_date'], r['acq_time'],
            r.get('satellite', 'Unknown'), r['instrument'], r['confidence'], r['frp'], r.get('daynight', ''),
            float(r.get('brightness') or r.get('bright_ti4') or 0)] for r in clean(rows, confidence=None)]}


@app.get('/data/runtime.json')
def runtime() -> dict:
    return {'api': True}


@app.get('/api/calendar')
def calendar(metric: str = Query('count', pattern='^(count|frp|anomaly)$'), result: dict = Depends(params)) -> dict:
    return {'metric': metric, 'days': result['series'], 'coverage_note': result['coverage_note']}


@app.get('/api/timeseries')
def timeseries(result: dict = Depends(params)) -> dict:
    return {'days': result['series'], 'annual': result['annual']}


@app.get('/api/anomalies')
def anomalies(result: dict = Depends(params)) -> dict:
    return {'days': result['anomalies'], 'baseline': 'Same calendar day +/-15 days in other displayed years; at least 60 days and 2 other years.'}


@app.get('/api/critical-periods')
def critical_periods(result: dict = Depends(params)) -> dict:
    return {'periods': result['critical_periods'], 'method': '7-day centered mean; 20% of annual rolling peak.'}


@app.get('/api/hotspots')
def hotspots(date: str | None = None, result: dict = Depends(params)) -> dict:
    rows = [r for r in result['hotspots'] if date is None or r['acq_date'] == date]
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [r['longitude'], r['latitude']]}, 'properties': r} for r in rows]}


@app.get('/api/calibration')
def calibration(region: str = 'borneo', start: str = '2019-01-01', end: str = '2023-12-31') -> dict:
    return query(region, start, end, 'MODIS,VIIRS', 30, .25, None)['calibration']


@app.get('/api/grid')
def grid(result: dict = Depends(params)) -> dict:
    return {'cells': result['grid'], 'note': 'Raw sensor aggregates; display grid does not alter the independent 0.01-degree matching lattice.'}


if (ROOT/'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT/'dist', html=True), name='frontend')
