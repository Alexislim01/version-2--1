# FINAL integration

The Historical record navigation entry runs alongside the existing explorer. It uses the scientific direction and reference scale specified in FINAL: Aqua MODIS to S-NPP VIIRS-equivalent detections.

## Requirement mapping

| Supplied function / result | Website implementation |
| --- | --- |
| Aqua 2003–2020 and S-NPP 2012–2020 inputs | Cleaned point shards for all 18 years; original inputs in the downloadable source archive; SHA-256 provenance |
| Vegetation, satellite and confidence cleaning; footprint duplicates | Bundler invokes the supplied simulation cleaning and representative-selection functions; the observed calendar is checked against every month's cleaned points |
| 0.25° monthly day/night features | Pipeline feature-building profile invokes `build_features.py`; all temporal/spatial model settings are explained under Method |
| Baselines and seven fusion methods | Full seven-method LOYO table; method-by-year inspection; exam/tuning/all-year comparisons; supplied selection rule |
| Independent held-out validation | Workbooks loaded as values, with no invented scores; January 2012 excluded; monthly WAPE and other metrics preserved |
| Indonesia and 200/800-tree checks | Accuracy country selector and model-size table; Indonesia map data require a new local run with FIRMS download |
| Fusion G1 conversion and hole gate | Complete local pipeline invokes the supplied model, including the G1 rule and historical climate exclusion |
| Pairing / analogue simulation / Poisson counts / five seeds | Simulation report, paired/hole map filters, five-run totals, control metrics, distribution figures and source CSVs |
| Historical points, 2003–2011 | All nine CSVs rendered on the map; synthetic flags, origins, parent IDs and run numbers retained in exports |
| Burning calendar, 2003–2020 | All 216 delivered monthly expectations/observations, click-to-map, source hatching, partial coverage, anomaly metric and CSV/PNG downloads |
| Annual totals and fire-season timing | Annual chart and bars; choose a year to view its peak month; largest positive same-month anomalies |
| Area and date interaction | Country/subregion and day/night scope, inclusive year range, individual months, rectangle/polygon drawing and GeoJSON with holes |
| Continuity and large-year bias | Out-of-sample annual gaps; separate in-sample reference; explicit 15–24% large-year underestimation note |
| Reproduction | Feature / validation / complete profiles; optional download, 36-setting tuning search, 200/800 trees; isolated runs, logs, cancellation and downloadable files |
| Use newly computed results | Successful complete runs produce a web bundle; Load this run replaces the historical workspace's points/calendar/reports; delivered results remain available |
| All explanations and results | Original workbook, CSV, figure and bilingual document downloads with checksums; downloadable Python source and Malaysia inputs |

## Scientific distinctions

- The original explorer uses a MODIS-equivalent descriptive transfer. The historical workspace uses the supplied VIIRS-equivalent model. Their units and validation claims are separate.
- National estimates before 2012 are the delivered Fusion G1 expectations, not the number of points in one simulation. Regional and day/night historical selections aggregate synthetic run 1 and are labeled accordingly.
- Layer visibility changes map/export points, not the underlying harmonized calendar. Aqua is shown as a separate observed layer and is not added to S-NPP calendar counts.
- FRP displays sum the observed or simulated record points; they are not a fitted G1 FRP estimate or integrated energy.
- January 2012 is partial. The supplied national baseline is preserved; regional baselines exclude partial January. A zero regional median yields an unavailable percentage rather than a fabricated anomaly.
- Synthetic points are blue and retain `is_synthetic`, `sim_source`, `sim_parent_modis`, `sim_run`, and `SIM1.0` on export. The original observation importer rejects synthetic CSVs.
- No new country, year, individual-fire accuracy, or ≤15% error achievement is asserted beyond the delivered results. An empty area outside the country means no points in this dataset.
- The simulation seed range is distinct from full model uncertainty. The nine-year mean and exam-year mean are selectable and retain their different variability ratios.

## Data and deployment

`scripts/build_final_data.py` packages the source results in `frontend/public/data/final`. The checked-in bundle contains 363,842 points: 53,927 observed Aqua, 144,253 observed S-NPP, and 165,662 synthetic run 1 points. It includes 216 calendar rows and original downloads. `manifest.json` records point counts, input/download hashes and the preparation date.

The static website, including a repository subpath such as GitHub Pages, can explore all packaged data and download all files. The Python job screen requires the FastAPI service; unavailable services receive an explicit connection state. API compute requests validate country/profile/tree settings, reject unrelated browser origins, allow one concurrent job, isolate each run, restrict file paths and mark interrupted runs after server restart.

New complete runs are stored under `artifacts/final-jobs`. The UI loads the run through `/api/final/jobs/<id>/bundle/`; it does not overwrite the delivered bundle. `environment.json` records package versions. One complete quick run and another complete run initiated through the website were executed during integration; both completed the full feature → LOYO → simulation → calendar workflow and selected Fusion G1. The local scikit-learn 1.7.2 fit differs slightly from the supplied workbook values, so new and delivered results remain separate.

## Verification

```powershell
npm.cmd run build
npm.cmd run test:selection
npm.cmd run test:final
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:BASE_URL='http://127.0.0.1:5178/'
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
npm.cmd run test:final-ui
```

The model checks reconcile the delivered national calendar, actual observation counts, regional/night filtering, January exclusion, empty areas, polygon holes and synthetic provenance. All 22 Python tests and both TypeScript suites pass. All 14 historical browser checks pass, including six accessibility scans without violations. The original explorer's seven layout/accessibility checks and twelve interaction checks also pass. An additional real-job check loads the completed regenerated bundle, restores the delivered bundle and cancels an actual feature-building process. On Windows, cancellation terminates the owned interpreter's child process tree. Browser artifacts are in ignored `artifacts/final-qa`.

The optional full 36-setting search and live NASA downloads are exposed as pipeline options. The executed complete runs used the supplied tuning choice and bundled Malaysia inputs.
