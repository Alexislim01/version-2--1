# code — the whole system in one command

```bash
pip install -r requirements.txt
python run_all.py
```

Malaysia's data are already in `data/raw/`, so this runs offline. A full run takes about 11 minutes on a laptop.

## Input → output

### What you put in (`data/raw/`)
Two kinds of **NASA FIRMS standard country-year CSVs**, for **the same country**:

| Folder | Files | Years | Role |
|---|---|---|---|
| `data/raw/modis/` | `modis_{year}_{Country}.csv` | **2003–2020** | The data to convert. 2003–2011 are converted; 2012–2020 are used to learn the conversion |
| `data/raw/viirs-snpp/` | `viirs-snpp_{year}_{Country}.csv` | **2012–2020** | The answer key for learning and testing (S-NPP VIIRS) |

**MODIS alone is not enough:** the system learns the MODIS → VIIRS conversion for that country from the years when both satellites were flying (2012–2020). `python run_all.py --download --country <Name>` fetches both kinds automatically (no login).

### What you get out (`output/`) — 6 kinds

| # | Output | Content |
|---|---|---|
| 1 | `synthetic_viirs/viirs-sim_{year}_{Country}.csv` (9 files, 2003–2011) + `sim_runs_summary.csv` | **Synthetic S-NPP VIIRS detections**, same 15 columns as a FIRMS VIIRS CSV + 4 columns marking them as synthetic |
| 2 | `calendar_2003_2020_{Country}.csv` | **Burning calendar**: one row per month, S-NPP-equivalent count, estimated/observed, median, anomaly % |
| 3 | `loyo_{country}.xlsx` | **Accuracy test**: 7 methods × 9 held-out years, and the method chosen |
| 4 | `sim_eval_{country}.xlsx` | **Simulation test**: synthetic vs real VIIRS on held-out years, vs a random control |
| 5 | `handover_{country}.xlsx` | **Yearly totals** 2003–2014 and the 2011/2012 continuity check |
| 6 | `figures/` (7 PNG) + `run_log.json` | Timeline, map, distribution plots; time spent per step |

Every column is explained in `../results/README.md`.

## Options

| Command | What it does |
|---|---|
| `python run_all.py` | All steps for Malaysia |
| `python run_all.py --download --country Indonesia` | Download FIRMS files for another country, then run everything |
| `python run_all.py --steps features,loyo` | Only some steps |
| `python run_all.py --quick` | Skip the simulation settings search (uses K=5, α=0, jitter 0.375 km) |
| `python run_all.py --trees 800` | Bigger forests (same scores, slower) |
| `--raw`, `--work`, `--out` | Use other folders |

## Files

| File | Step | Job |
|---|---|---|
| `run_all.py` | — | Entry point; runs the steps in order |
| `config.py` | — | All paths and settings |
| `download.py` | download | Gets FIRMS files, checks each file size against the FIRMS index |
| `build_features.py` | features | Cleans (vegetation fires, nominal/high confidence, duplicate removal), grids to 0.25° × month × day/night, builds MODIS-only features |
| `loyo.py` | loyo | Leave-one-year-out test of 7 methods; picks the method by a fixed rule |
| `pair_v2.py` | (used by sim) | MODIS–VIIRS footprint pairing and duplicate detection |
| `sim_viirs.py` | sim | Point-level synthetic VIIRS: pairing, settings search, test, 2003–2011 files, figures |
| `make_calendar.py` | calendar | Burning calendar CSV |
| `requirements.txt` | — | Python packages |

`work/` (created on first run) holds intermediate files: feature table, predictions, simulation cache.

## Rules built into the code
- Inputs are MODIS-only; year, cell ID and anything from VIIRS are never features.
- Training years 2012–2020 (before Aqua's orbit drift). January 2012 is never scored.
- "Normal fire" features use Aqua 2003–2011, leaving out the year being converted.
- Fixed random seeds: identical numbers on every run.
