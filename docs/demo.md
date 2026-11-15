# Three-minute demonstration

**0:00–0:30 — The problem.** Open Fire explorer with the default Borneo view, 2019–2023. Explain that the sample contains Malaysia's part of Borneo. MODIS uses larger pixels; VIIRS sees more small thermal detections, so more detections do not automatically mean more burning.

**0:30–1:05 — One connected record.** Scroll to the raw-versus-harmonized series. Toggle the raw VIIRS line, then restore it. The raw sensitivity difference is much larger than the calibrated MODIS-equivalent record. Open Harmonization to inspect actual R², bias, and the month-specific fits. The measured agreement is imperfect, which the app shows openly.

**1:05–1:40 — Patterns over time.** Return to Fire explorer. Switch the burning calendar from count to FRP, then anomaly. Hover a day and click it to filter the map. Use the arrow buttons or keyboard arrow keys to move through days.

**1:40–2:15 — Critical periods.** Open Insights. Compare annual totals with coverage day counts, inspect seasonal peaks, then select one unusual day to return to the filtered map. Explain how the other-year seasonal baseline differs from a fixed alert threshold.

**2:15–2:40 — Reproducibility.** Export the daily CSV and GeoJSON. Open the data dialog to show official source files, then Method & sources to explain the matching lattice, calibration, and limitations.

**2:40–3:00 — Extend honestly.** Select California: the app shows missing coverage rather than invented observations. Import official FIRMS CSVs or add a local MAP_KEY and run ingestion. Explain that a full 2000–present record and the 2012 transition test require those additional archives; the five-year demo cannot establish that continuity.
