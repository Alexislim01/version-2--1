"""Shared settings. run_all.py sets these before importing the other modules.

Defaults keep everything inside this folder, so the code runs on any computer.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
COUNTRY = "Malaysia"                 # FIRMS country name, e.g. "Malaysia", "Indonesia"
RAW = BASE / "data" / "raw"          # raw/modis/modis_{year}_{COUNTRY}.csv, raw/viirs-snpp/...
WORK = BASE / "work"                 # feature tables, predictions, caches
OUT = BASE / "output"                # final results (xlsx, csv, figures)
TREES = 200                          # random-forest size (800 gives the same scores)

TRAIN_YEARS = range(2012, 2021)      # S-NPP and Aqua overlap before Aqua's orbit drift
EARLY_YEARS = range(2003, 2012)      # Aqua-only years that are converted
EXAM_YEARS = {2012, 2019, 2020}      # pre-registered exam years (January 2012 never scored)


def paths() -> dict:
    return {
        "table": WORK / f"feature_table_{COUNTRY}.parquet",
        "meta": WORK / f"feature_meta_{COUNTRY}.json",
        "loyo_xlsx": OUT / f"loyo_{COUNTRY.lower()}.xlsx",
        "loyo_partial": WORK / f"loyo_{COUNTRY.lower()}_partial.csv",
        "loyo_pred": WORK / f"loyo_{COUNTRY.lower()}_predictions.parquet",
        "cache": WORK / "sim_cache",
        "figures": OUT / "figures",
        "synthetic": OUT / "synthetic_viirs",
    }
