"""Download FIRMS Area API batches or import archive CSV, preserving provenance."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.core import clean


def main() -> None:
    from dotenv import load_dotenv
    import pandas as pd
    load_dotenv(ROOT / '.env')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bbox', default='108,-5,120,8')
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--source', choices=['MODIS_SP','MODIS_NRT','VIIRS_SNPP_SP','VIIRS_SNPP_NRT','VIIRS_NOAA20_SP','VIIRS_NOAA20_NRT','VIIRS_NOAA21_SP','VIIRS_NOAA21_NRT'], default='MODIS_SP')
    p.add_argument('--csv', type=Path, help='Import an existing official archive instead of using the API')
    args = p.parse_args()
    bbox = [float(v) for v in args.bbox.split(',')]
    if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        p.error('Invalid west,south,east,north bounding box')
    if not 2000 <= args.year <= date.today().year:
        p.error('Year outside the satellite archive range')
    raw_dir = ROOT/'data'/'raw'; raw_dir.mkdir(exist_ok=True)
    files, provenance = [], []
    if args.csv:
        files = [args.csv.resolve()]
    else:
        key = os.getenv('FIRMS_MAP_KEY', '')
        if not key:
            p.error('Add FIRMS_MAP_KEY to .env or use --csv. Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/')
        # Verify availability before requesting a year; never treat HTTP 200 text errors as data.
        availability_url = f'https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/{args.source}'
        try:
            with urllib.request.urlopen(availability_url, timeout=60) as response:
                availability = list(csv.DictReader(response.read().decode('utf-8-sig').splitlines()))
        except Exception:
            p.error('Could not check FIRMS availability. Check key and connection; key is not logged.')
        if not availability or 'min_date' not in availability[0]:
            p.error('FIRMS did not return product availability; check your key.')
        begin = max(date(args.year, 1, 1), date.fromisoformat(availability[0]['min_date']))
        end = min(date(args.year, 12, 31), date.fromisoformat(availability[0]['max_date']))
        if begin > end:
            p.error('Requested year is outside this product’s available dates.')
        while begin <= end:
            days = min(5, (end-begin).days+1)
            digest = hashlib.sha256(args.bbox.encode()).hexdigest()[:10]
            file = raw_dir/f'{args.source}_{digest}_{begin}_{days}.csv'
            if not file.exists():
                url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{args.source}/{args.bbox}/{days}/{begin}'
                content = None
                for attempt in range(3):
                    try:
                        with urllib.request.urlopen(url, timeout=120) as response:
                            candidate = response.read()
                        if b'latitude' not in candidate.split(b'\n')[0]:
                            raise ValueError('Unexpected response')
                        content = candidate
                        break
                    except Exception:
                        time.sleep(2**attempt)
                if content is None:
                    p.error(f'Download failed for {begin}; cached earlier batches are safe. Retry later.')
                file.write_bytes(content)
                time.sleep(.35)
            files.append(file)
            provenance.append({'start': str(begin), 'end': str(begin+timedelta(days=days-1)), 'sensor': 'MODIS' if args.source.startswith('MODIS') else 'VIIRS', 'product': args.source, 'bbox': bbox, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
            begin += timedelta(days=days)
    records = []
    for file in files:
        with file.open(newline='', encoding='utf-8-sig') as f:
            records.extend(csv.DictReader(f))
    records = [r for r in clean(records) if r['acq_date'].startswith(str(args.year))
               and bbox[0] <= r['longitude'] <= bbox[2] and bbox[1] <= r['latitude'] <= bbox[3]]
    if not records:
        p.error('No accepted detections. No fabricated records were created.')
    frame = pd.DataFrame(records)
    frame['year'] = frame['acq_date'].str[:4]
    out = ROOT/'data'/'parquet'
    out.mkdir(exist_ok=True)
    # One file per product/year, atomically replaced, so reruns cannot duplicate observations.
    for year, partition in frame.groupby('year'):
        directory = out/f'year={year}'; directory.mkdir(exist_ok=True)
        target = directory/f'{args.source}.parquet'
        temp = target.with_suffix('.tmp')
        partition.drop(columns='year').to_parquet(temp, index=False)
        temp.replace(target)
    metadata = out/f'{args.source}_{args.year}.coverage.json'
    if not provenance:
        # An imported CSV's absence of detections does not establish whole-year coverage.
        provenance = [{'start': str(d), 'end': str(d), 'sensor': str(frame.iloc[0]['instrument']), 'product': args.source, 'bbox': bbox} for d in sorted(frame.acq_date.unique())]
    metadata.write_text(json.dumps(provenance, indent=2))
    print(f'Wrote {len(records):,} accepted observations to {out}. Restart the API to reload.')


if __name__ == '__main__':
    main()
