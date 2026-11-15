"""FIRMS processing. Missing observations are never silently converted to zero.

Coverage describes complete queried intervals, not cloud-free observing effort.
Calibration is exploratory, in-sample, and must not be read as burned area.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import median, pstdev
from typing import Any

Record = dict[str, Any]


def clean(records: list[Record], confidence: int | None = 30) -> list[Record]:
    result, seen = [], set()
    for raw in records:
        try:
            r = dict(raw)
            r['latitude'], r['longitude'], r['frp'] = (float(r[k]) for k in ('latitude', 'longitude', 'frp'))
            if not all(math.isfinite(r[k]) for k in ('latitude', 'longitude', 'frp')):
                continue
            if not (-90 <= r['latitude'] <= 90 and -180 <= r['longitude'] <= 180 and r['frp'] >= 0):
                continue
            r['acq_date'] = date.fromisoformat(str(r['acq_date'])).isoformat()
            r['instrument'] = str(r.get('instrument') or ('VIIRS' if 'bright_ti4' in r else 'MODIS')).upper()
            value = str(r.get('confidence', '')).lower()
            if r['instrument'] == 'VIIRS':
                value = {'low': 'l', 'nominal': 'n', 'high': 'h'}.get(value, value)
                if confidence is not None and (value not in ('n', 'h') or (confidence > 80 and value != 'h')):
                    continue
            elif confidence is not None and float(value) < confidence:
                continue
            r['confidence'] = value
            r['acq_time'] = str(r.get('acq_time', '0')).zfill(4)
            if len(r['acq_time']) != 4 or int(r['acq_time'][:2]) > 23 or int(r['acq_time'][2:]) > 59:
                continue
            key = tuple(str(r.get(k, '')) for k in ('latitude', 'longitude', 'acq_date', 'acq_time', 'satellite', 'instrument'))
            if key not in seen:
                result.append(r)
                seen.add(key)
        except (ValueError, TypeError, KeyError):
            continue
    return result


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[:2]
        xj, yj = ring[j][:2]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_geometry(r: Record, geometry: Record | None) -> bool:
    if not geometry:
        return True
    polys = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    return any(point_in_ring(r['longitude'], r['latitude'], poly[0]) and
               not any(point_in_ring(r['longitude'], r['latitude'], hole) for hole in poly[1:]) for poly in polys)


def grid_records(records: list[Record], grid: float = .25) -> list[Record]:
    if grid not in (.1, .25, .5):
        raise ValueError('Grid must be 0.1, 0.25 or 0.5 degrees.')
    cells: dict[tuple, Record] = {}
    for r in records:
        # 0.01 degrees is an approximate 1 km matching lattice, independent of display grid.
        key = (r['acq_date'], r['instrument'], math.floor(r['latitude'] / grid), math.floor(r['longitude'] / grid))
        cell = cells.setdefault(key, {'date': key[0], 'sensor': key[1], 'cell': list(key[2:]), 'detection_count': 0, 'pixels': {}})
        cell['detection_count'] += 1
        pixel = (math.floor(r['latitude'] / .01), math.floor(r['longitude'] / .01))
        cell['pixels'][pixel] = max(cell['pixels'].get(pixel, 0), r['frp'])
    return [{**{k: v for k, v in c.items() if k != 'pixels'}, 'unique_pixels': len(c['pixels']),
             'frp': sum(c['pixels'].values())} for c in cells.values()]


def fit_transfer(pairs: list[tuple[float, float]]) -> Record:
    """Deterministic Theil-Sen fit y=MODIS, x=VIIRS. Never claim sparse fits."""
    pairs = [(x, y) for x, y in pairs if x > 0 or y > 0]
    if len(pairs) < 20 or len(set(x for x, _ in pairs)) < 3:
        return {'available': False, 'n': len(pairs), 'reason': 'At least 20 informative overlap days and three VIIRS values are required.'}
    sampled = pairs[::max(1, math.ceil(len(pairs) / 120))]
    slopes = [(y2-y1)/(x2-x1) for i, (x1, y1) in enumerate(sampled) for x2, y2 in sampled[i+1:] if x2 != x1]
    slope = max(0, median(slopes))
    intercept = median([y - slope*x for x, y in pairs])
    predicted = [max(0, slope*x + intercept) if x > 0 else 0 for x, _ in pairs]
    ys = [y for _, y in pairs]
    residual = [p-y for p, y in zip(predicted, ys)]
    mean_y = sum(ys)/len(ys)
    total = sum((y-mean_y)**2 for y in ys)
    return {'available': True, 'n': len(pairs), 'slope': slope, 'intercept': intercept,
            'r2': 1-sum(e*e for e in residual)/total if total else None,
            'bias': sum(residual)/len(residual), 'raw_bias': sum(x-y for x, y in pairs)/len(pairs),
            'rmse': math.sqrt(sum(e*e for e in residual)/len(residual)), 'spread': 1.96*pstdev(residual)}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0
    v = sorted(values)
    i = (len(v)-1)*p
    lo, hi = math.floor(i), math.ceil(i)
    return v[lo] + (v[hi]-v[lo])*(i-lo)


def analyze(records: list[Record], coverage: list[Record], start: str, end: str,
            bbox: list[float], grid: float = .25, confidence: int = 30,
            sensors: tuple[str, ...] = ('MODIS', 'VIIRS'), geometry: Record | None = None) -> Record:
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    if finish < begin or (finish-begin).days > 12000:
        raise ValueError('Choose an ordered date range of at most 32 years.')
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90) or (east-west)*(north-south) > 15000:
        raise ValueError('AOI must be a valid bounding box smaller than 15,000 square degrees.')
    selected = [r for r in clean(records, confidence) if west <= r['longitude'] <= east and south <= r['latitude'] <= north
                and r['instrument'] in sensors and in_geometry(r, geometry)]
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for cell in grid_records(selected, grid):
        v = grouped[cell['date']][cell['sensor']]
        v[0] += cell['unique_pixels']; v[1] += cell['frp']; v[2] += cell['detection_count']
    def covered(d: str, sensor: str) -> bool:
        return sensor in sensors and any(c['sensor'] == sensor and c['start'] <= d <= c['end'] for c in coverage)
    # Calibration uses all available overlap years in the AOI, independent of display range.
    all_dates = sorted(grouped)
    pairs = {metric: [(grouped[d]['VIIRS'][idx], grouped[d]['MODIS'][idx]) for d in all_dates
                      if covered(d, 'MODIS') and covered(d, 'VIIRS')] for metric, idx in [('count', 0), ('frp', 1)]}
    global_fit = {metric: fit_transfer(p) for metric, p in pairs.items()}
    fits = {}
    for month in range(1, 13):
        fits[month] = {}
        for metric, idx in [('count', 0), ('frp', 1)]:
            fit = fit_transfer([(grouped[d]['VIIRS'][idx], grouped[d]['MODIS'][idx]) for d in all_dates
                                if int(d[5:7]) == month and covered(d, 'MODIS') and covered(d, 'VIIRS')])
            fits[month][metric] = {**(fit if fit['available'] else global_fit[metric]), 'scope': 'month' if fit['available'] else 'AOI fallback'}
    series = []
    current = begin
    while current <= finish:
        d = current.isoformat()
        mc, vc = covered(d, 'MODIS'), covered(d, 'VIIRS')
        values = grouped[d]
        item: Record = {'date': d, 'modis': values['MODIS'][0] if mc else None, 'viirs': values['VIIRS'][0] if vc else None,
                        'raw_modis_frp': values['MODIS'][1] if mc else None, 'raw_viirs_frp': values['VIIRS'][1] if vc else None,
                        'detections': sum(values[s][2] for s in sensors), 'source': 'No coverage'}
        for metric, idx in [('count', 0), ('frp', 1)]:
            fit = fits[current.month][metric]
            raw = values['VIIRS'][idx]
            calibrated = max(0, raw*fit['slope'] + fit['intercept']) if vc and fit['available'] and raw > 0 else (0 if vc and fit['available'] else None)
            m = values['MODIS'][idx] if mc else None
            value = (m+calibrated)/2 if m is not None and calibrated is not None else (m if m is not None else calibrated)
            item['harmonized_'+metric] = value
            if metric == 'count':
                item['calibrated_viirs'] = calibrated
                spread = fit.get('spread', 0)/(2 if mc else 1) if calibrated is not None else 0
                item['lower'] = max(0, value-spread) if value is not None else None
                item['upper'] = value+spread if value is not None else None
                item['source'] = 'Both sensors' if mc and calibrated is not None else ('MODIS only' if mc else ('Calibrated VIIRS' if calibrated is not None else ('Uncalibrated VIIRS' if vc else 'No coverage')))
        series.append(item)
        current += timedelta(days=1)
    # Same calendar day +/- 15 days across OTHER years, excluding February 29 drift.
    available = [d for d in series if d['harmonized_count'] is not None]
    baseline_buckets: list[list[tuple[str, float]]] = [[] for _ in range(366)]
    def day_of_year(d: str) -> int:
        return (date(2000, int(d[5:7]), int(d[8:10]))-date(2000, 1, 1)).days
    for d in available:
        center = day_of_year(d['date'])
        for offset in range(-15, 16):
            baseline_buckets[(center+offset) % 366].append((d['date'][:4], d['harmonized_count']))
    for d in series:
        sample = [(year, value) for year, value in baseline_buckets[day_of_year(d['date'])] if year != d['date'][:4]]
        baseline = [value for _, value in sample]
        years = {year for year, _ in sample}
        valid = len(baseline) >= 60 and len(years) >= 2 and d['harmonized_count'] is not None
        d['median'] = median(baseline) if valid else None
        d['p90'] = percentile(baseline, .9) if valid else None
        d['p95'] = percentile(baseline, .95) if valid else None
        value = d['harmonized_count']
        d['percentile'] = 100*sum(v < value for v in baseline)/len(baseline) if valid else None
        sd = pstdev(baseline) if valid else 0
        d['anomaly'] = (value-sum(baseline)/len(baseline))/sd if valid and sd else None
        d['unusual'] = valid and value > 0 and value > d['p95']
    periods, annual = [], []
    for year in sorted({d['date'][:4] for d in available}):
        days = [d for d in available if d['date'].startswith(year)]
        annual.append({'year': year, 'count': sum(d['harmonized_count'] for d in days), 'covered_days': len(days)})
        rolling = [(sum(x['harmonized_count'] for x in days[max(0, i-3):i+4])/len(days[max(0, i-3):i+4]), d) for i, d in enumerate(days)]
        peak = max(rolling, key=lambda v: v[0])
        active = [d for value, d in rolling if value > .2*peak[0] and value > 0]
        if active:
            periods.append({'year': year, 'start': active[0]['date'], 'peak': peak[1]['date'], 'end': active[-1]['date'], 'intensity': peak[0]})
    return {'series': series, 'calibration': {'global': global_fit, 'monthly': fits, 'method': 'Theil–Sen; in-sample fit; negative predictions clipped to zero'},
            'anomalies': [d for d in series if d['unusual']], 'critical_periods': sorted(periods, key=lambda p: -p['intensity']),
            'annual': annual, 'hotspots': [r for r in selected if start <= r['acq_date'] <= end],
            'grid': grid_records([r for r in selected if start <= r['acq_date'] <= end], grid),
            'coverage_note': 'Coverage indicates a complete supplied file/query, not guaranteed satellite observation. No detection is not proof of no fire.'}
