"""Rebuild the bundled, genuine 2019–2023 Malaysian FIRMS archive."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://firms.modaps.eosdis.nasa.gov/data/country/'


def download(item: tuple[str, int]) -> tuple[list[dict], dict]:
    product, year = item
    name = f'{product}_{year}_Malaysia.csv'
    file = ROOT/'data'/'raw'/name
    file.parent.mkdir(exist_ok=True)
    if not file.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(BASE+name, timeout=120) as r:
                    content = r.read()
                if not content.startswith(b'latitude,longitude'):
                    raise ValueError('Unexpected archive response')
                file.write_bytes(content)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
    content = file.read_bytes()
    records = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
    # Preserve every original scientific field; add only missing instrument labels.
    for r in records:
        r['instrument'] = 'MODIS' if product == 'modis' else 'VIIRS'
    print(f'{name}: {len(records):,} genuine observations', flush=True)
    return records, {'sensor': 'MODIS' if product == 'modis' else 'VIIRS', 'product': product,
                     'start': f'{year}-01-01', 'end': f'{year}-12-31', 'country': 'Malaysia',
                     'url': BASE+name, 'sha256': hashlib.sha256(content).hexdigest(), 'records': len(records)}


def main() -> None:
    tasks = [(product, year) for product in ('modis', 'viirs-snpp', 'viirs-jpss1') for year in range(2019, 2024)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts = list(pool.map(download, tasks))
    records = [r for rows, _ in parts for r in rows]
    metadata = {'title': 'NASA FIRMS · Malaysia archive', 'start': '2019-01-01', 'end': '2023-12-31',
                'coverage': [c for _, c in parts], 'country': 'Malaysia',
                'note': 'Complete country archive files. Borneo and Southeast Asia views contain Malaysian territory only; other countries are not covered.'}
    headers = sorted({k for r in records for k in r})
    with (ROOT/'data'/'sample.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader(); writer.writerows(records)
    (ROOT/'data'/'provenance.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    compact = []
    for r in records:
        compact.append([float(r['latitude']), float(r['longitude']), r['acq_date'], r['acq_time'],
                        r['satellite'], r['instrument'], r['confidence'], float(r['frp']), r['daynight'],
                        float(r.get('brightness') or r.get('bright_ti4') or 0)])
    public = ROOT/'frontend'/'public'/'data'
    public.mkdir(parents=True, exist_ok=True)
    (public/'sample.json').write_text(json.dumps({'metadata': metadata, 'rows': compact}, separators=(',', ':')), encoding='utf-8')
    print(f'Bundled {len(records):,} observations; provenance and checksums saved.', flush=True)


if __name__ == '__main__':
    main()
