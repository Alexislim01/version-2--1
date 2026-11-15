"""MODIS -> S-NPP VIIRS harmonization: the whole system in one command.

    python run_all.py                       # Malaysia, data already in data/raw
    python run_all.py --download            # fetch FIRMS files first (no login needed)
    python run_all.py --country Indonesia --download
    python run_all.py --steps features,loyo # run only some steps
    python run_all.py --quick               # skip simulation tuning (uses K=5, alpha=0, jitter=0.375 km)

Steps (in order):
  download   FIRMS country-year CSVs: Aqua MODIS 2003-2020, S-NPP VIIRS 2012-2020
  features   clean, de-duplicate, grid to 0.25 deg x month x day/night  (build_features.py)
  loyo       leave-one-year-out test of 7 methods, picks the best        (loyo.py)
  sim        point-level synthetic VIIRS: pair, tune, exam, 2003-2011    (sim_viirs.py)
  calendar   2003-2020 burning calendar CSV                              (make_calendar.py)

Outputs go to output/ (results) and work/ (intermediate files).
Needs Python 3.10+ with: pandas numpy scipy scikit-learn pyproj matplotlib openpyxl pyarrow
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import config

ALL_STEPS = ["download", "features", "loyo", "sim", "calendar"]
QUICK_CHOICE = {"K": 5, "alpha": 0.0, "jitter_km": 0.375}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", default=config.COUNTRY)
    ap.add_argument("--raw", type=Path, default=config.RAW)
    ap.add_argument("--work", type=Path, default=config.WORK)
    ap.add_argument("--out", type=Path, default=config.OUT)
    ap.add_argument("--trees", type=int, default=config.TREES)
    ap.add_argument("--steps", default=",".join(s for s in ALL_STEPS if s != "download"))
    ap.add_argument("--download", action="store_true", help="add the download step")
    ap.add_argument("--quick", action="store_true", help="skip the simulation parameter search")
    a = ap.parse_args(argv)

    config.COUNTRY, config.RAW, config.WORK, config.OUT, config.TREES = a.country, a.raw, a.work, a.out, a.trees
    for d in (config.WORK, config.OUT):
        d.mkdir(parents=True, exist_ok=True)
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    if a.download and "download" not in steps:
        steps.insert(0, "download")
    bad = [s for s in steps if s not in ALL_STEPS]
    if bad:
        ap.error(f"unknown steps {bad}; choose from {ALL_STEPS}")
    steps.sort(key=ALL_STEPS.index)
    sys.path.insert(0, str(config.BASE))

    log = []
    for step in steps:
        t0 = time.time()
        print(f"\n===== {step} ({config.COUNTRY}) =====", flush=True)
        if step == "download":
            import download
            download.download(config.COUNTRY, config.RAW)
        elif step == "features":
            import build_features
            build_features.build(config.RAW, config.WORK, config.TRAIN_YEARS.start,
                                 config.TRAIN_YEARS.stop - 1, config.COUNTRY)
        elif step == "loyo":
            import loyo
            loyo.main(config.COUNTRY, config.TREES, None)
        elif step == "sim":
            import sim_viirs
            cache = config.paths()["cache"]
            cache.mkdir(parents=True, exist_ok=True)
            if a.quick:
                (cache / "chosen_sim.json").write_text(json.dumps(QUICK_CHOICE), encoding="utf-8")
                sim_viirs.main("pair")
                sim_viirs.main("exam")
                sim_viirs.main("hist")
            else:
                sim_viirs.main("all")
        elif step == "calendar":
            import make_calendar
            make_calendar.build()
        log.append({"step": step, "seconds": round(time.time() - t0, 1)})
        print(f"----- {step} done in {log[-1]['seconds']} s", flush=True)
    (config.OUT / "run_log.json").write_text(json.dumps(
        {"country": config.COUNTRY, "trees": config.TREES, "quick": a.quick, "steps": log}, indent=2), encoding="utf-8")
    print("\nall done ->", config.OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
