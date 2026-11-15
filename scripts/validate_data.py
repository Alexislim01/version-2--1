"""Measure actual NASA sample results and write reproducible validation artifacts."""
from __future__ import annotations
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pipeline.core import analyze, clean, grid_records


def main() -> None:
    import pandas as pd
    with (ROOT/'data/sample.csv').open(newline='',encoding='utf-8') as file:
        rows=list(csv.DictReader(file))
    provenance=json.loads((ROOT/'data/provenance.json').read_text())
    tick=time.perf_counter()
    result=analyze(rows,provenance['coverage'],'2019-01-01','2023-12-31',[108,-5,120,8])
    seconds=time.perf_counter()-tick
    accepted=clean(rows)
    directory=ROOT/'data/aggregates';directory.mkdir(exist_ok=True)
    frame=pd.DataFrame(grid_records(accepted))
    frame['year']=frame['date'].str[:4]
    for year,part in frame.groupby('year'):
        target=directory/f'year={year}';target.mkdir(exist_ok=True)
        part.drop(columns='year').to_parquet(target/'daily-grid.parquet',index=False)
    pd.DataFrame(result['series']).to_parquet(directory/'borneo-daily.parquet',index=False)
    validation={'region':'Borneo — Malaysian territory only','raw_records':len(rows),'accepted_records_malaysia':len(accepted),
                'accepted_records_aoi':len(result['hotspots']),'period':['2019-01-01','2023-12-31'],
                'calibration':result['calibration'],'unusual_days':len(result['anomalies']),
                'analysis_seconds':round(seconds,3),'transition_2012':{'status':'unavailable','reason':'The bundled dataset starts in 2019. Ingest pre/post-2012 records before testing transition continuity.'},
                'validation_scope':'Exploratory in-sample diagnostics. Not independent or ground-truth validation.'}
    (ROOT/'docs/validation.json').write_text(json.dumps(validation,indent=2,ensure_ascii=False),encoding='utf-8')
    monthly=defaultdict(lambda:{'modis':0.,'viirs':0.,'harmonized_count':0.})
    for day in result['series']:
        for key in ('modis','viirs','harmonized_count'):
            monthly[day['date'][:7]][key]+=day[key] or 0
    items=sorted(monthly.items());width,height=1100,430;left,right,top,bottom=70,30,100,65
    maximum=max(max(v.values()) for _,v in items)*1.1
    def x(i):return left+i/max(1,len(items)-1)*(width-left-right)
    def y(value):return height-bottom-value/maximum*(height-top-bottom)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#101c1f"/>',
         '<text x="45" y="42" fill="#e1e5df" font-family="sans-serif" font-size="24">FireAtlas | Real-data harmonization validation</text>',
         '<text x="45" y="68" fill="#a7b5b4" font-family="sans-serif" font-size="13">Malaysian Borneo | NASA FIRMS 2019-2023 | Monthly unique-pixel activity</text>']
    for i in range(5):
        v=maximum*i/4
        svg.extend([f'<line x1="{left}" x2="{width-right}" y1="{y(v)}" y2="{y(v)}" stroke="#334244" stroke-dasharray="3 5"/>',
                    f'<text x="{left-10}" y="{y(v)+4}" text-anchor="end" fill="#a7b5b4" font-family="sans-serif" font-size="11">{v:.0f}</text>'])
    for key,color in [('modis','#829aab'),('viirs','#b7b38a'),('harmonized_count','#edb47f')]:
        points=' '.join(f'{x(i):.2f},{y(v[key]):.2f}' for i,(_,v) in enumerate(items))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    for i,(label,_) in enumerate(items):
        if i%12==0:
            svg.append(f'<text x="{x(i)}" y="{height-bottom+24}" text-anchor="middle" fill="#a7b5b4" font-family="sans-serif" font-size="11">{label}</text>')
    svg.append('<text x="70" y="410" fill="#a7b5b4" font-family="sans-serif" font-size="11">Blue: raw MODIS | Sage: merged raw VIIRS | Amber: monthly calibrated harmonized record. In-sample; not burned area.</text></svg>')
    (ROOT/'docs/validation.svg').write_text('\n'.join(svg),encoding='utf-8')
    browser_csv=ROOT/'artifacts/fireatlas-borneo-2019-01-01.csv'
    if browser_csv.exists():
        with browser_csv.open(newline='',encoding='utf-8') as file:
            browser=list(csv.DictReader(file))
        errors=[]
        for py,js in zip(result['series'],browser):
            for key in ('harmonized_count','harmonized_frp','modis','viirs','lower','upper','anomaly'):
                if py[key] is None and js[key]=='':continue
                if py[key] is None or js[key]=='':errors.append((py['date'],key));continue
                if abs(py[key]-float(js[key]))>1e-8:errors.append((py['date'],key))
        parity={'compared_days':len(browser),'mismatches':len(errors),'sample_mismatches':errors[:5]}
        (ROOT/'docs/parity.json').write_text(json.dumps(parity,indent=2),encoding='utf-8')
        if errors or len(browser)!=len(result['series']):
            raise RuntimeError(f'Browser/API parity failed: {parity}')
        print(f'Browser/API parity: {len(browser)} days, zero mismatches.')
    print(f'Validated {len(rows):,} original records; analysis {seconds:.3f}s. Parquet aggregates and diagnostics written.')


if __name__=='__main__':
    main()
