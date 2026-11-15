# FINAL — MODIS → VIIRS hotspot harmonization (NASA Space Apps 2026)

| Folder | What it is for |
|---|---|
| `docs/` | **Explanation**: how the system works, how it was tested, how much to trust it (PDF, English and Chinese) |
| `results/` | **Latest test results**: all methods compared, every held-out year, Malaysia + Indonesia, plus the burning calendar and the synthetic VIIRS files. Every value is explained in `results/README.md` |
| `code/` | **The system**: `python run_all.py` runs everything. Malaysia's FIRMS data are included |

**In:** NASA FIRMS Aqua MODIS (2003–2020) + S-NPP VIIRS (2012–2020) CSVs for one country.
**Out:** synthetic VIIRS detections for 2003–2011, a 2003–2020 burning calendar, and accuracy reports.

**Accuracy (leave-one-year-out, monthly national error):** ≈ 85% without conversion → **17.1%** with Fusion G1 (Malaysia, 9 never-seen years); Indonesia 15.3%. Large fire years are under-estimated by ~15–24%. Synthetic points are a simulation, not observations.
