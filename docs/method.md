# Scientific method and assumptions

1. Keep genuine FIRMS records and their original attributes. Drop invalid coordinates, negative/nonfinite FRP, malformed times/dates, VIIRS low confidence, and MODIS confidence below the selected minimum (at least 30). At thresholds above 80 retain high-confidence VIIRS only; this is an explicit categorical rule, not a claim that VIIRS confidence is a percentage.
2. Remove exact duplicate instrument/satellite/coordinate/date/time records. Use an independent 0.01° matching lattice per instrument/day to merge repeat passes and the VIIRS platforms. Retain maximum FRP in each matching pixel. This is an approximate conservative proxy, not an exact fire-event inventory.
3. Aggregate to 0.1°, 0.25°, or 0.5° display cells per day/sensor. Keep raw detection count, unique matched pixel count, and summed representative FRP. AOI-wide totals are independent of display-grid selection.
4. Calibrate daily AOI totals in the overlap. Deterministic Theil–Sen estimates the median pairwise slope from at most 120 uniformly sampled informative overlap days, then the median intercept across all informative pairs. Require 20 informative days and at least 3 VIIRS values. Fit each calendar month; sparse months use the AOI-wide model. Fit count and FRP separately.
5. Predict `max(0, slope * VIIRS + intercept)` on positive VIIRS days; zero stays zero. Average that prediction with MODIS on overlapping coverage days. Use a sole available MODIS observation or calibrated VIIRS observation. Uncalibrated VIIRS is visible as raw data but is never silently converted to MODIS equivalents.
6. Coverage is a complete supplied country file or successfully queried API interval. It is not an exposure or cloud-free observing-effort correction. Missing coverage stays null. Malaysian country archives do not cover other countries within a broader preset AOI. Browser CSV imports default to observed dates, spatially filtered to detections actually in the AOI.
7. Describe overlap quality using in-sample R², mean predicted-minus-MODIS bias, raw VIIRS-minus-MODIS bias, and RMSE. Shade `1.96 * population standard deviation(residuals)`, halved when averaging two sensors. This is a residual-spread visualization, not a confidence interval. MODIS-only uncertainty is unknown; a zero-width model band must not imply perfect observation.
8. Climatology uses a ±15-day window on a leap-year calendar across other displayed years, requiring at least 60 baseline days from at least two other years. February 29 has its own calendar position. Flag strictly above the 95th percentile with positive activity. Return z-score only when baseline variance is nonzero.
9. Estimate annual fire-season descriptors using a centered 7-day mean and the first/last dates strictly above 20% of that year's rolling peak. These are descriptive endpoints, not guaranteed contiguous seasons. Annual comparisons must account for incomplete coverage; do not infer a long-term climatic trend from five years.

## Limits and outstanding validation

- Neither record identifies ground-truth burned area. Thermal sources may be vegetation fires, industrial heat, volcanoes, or other anomalies.
- Viewing geometries use WGS 84; degree-sized cells and the matching lattice vary in physical size with latitude. Cross-boundary fires may remain separate; neighboring fires can merge.
- Same-day averaging does not correct cloud/smoke occlusion, differing overpass times, different sensor responses, or changing observation effort.
- Both algorithms use all available AOI overlap years for calibration, independent of display range. Seasonal baselines use the displayed range.
- No 2012 transition is present in the 2019–2023 bundle. The validation report explicitly marks that test unavailable. A longer record and independent holdout validation are required before claiming transition continuity or operational reliability.
- Quantile mapping, exact fire-event matching, global job scheduling, and ground-truth validation are outside this implementation.

## Sources

- [NASA FIRMS country archive](https://firms.modaps.eosdis.nasa.gov/country/)
- [NASA FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/)
- [NASA archive product coverage](https://firms.modaps.eosdis.nasa.gov/download/)
- [Natural Earth public-domain boundaries](https://www.naturalearthdata.com/)

Original country-file URLs and SHA-256 checksums are saved in `data/provenance.json`. Cached downloads can be checked without exposing any MAP_KEY.
