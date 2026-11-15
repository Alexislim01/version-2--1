"""Package FINAL's delivered results and cleaned observations for the web app.

Run with the scientific Python environment: python scripts/build_final_data.py.
The supplied results stay intact. No fitted scores are invented or recomputed here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "FINAL"
POINT_COLUMNS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument",
                 "confidence", "frp", "daynight", "brightness", "scan", "track", "bright_ti5",
                 "is_synthetic", "sim_source", "sim_parent_modis", "sim_run"]


def native(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 6) if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
                               default=native), encoding="utf-8")


def workbook(path: Path) -> dict:
    from openpyxl import load_workbook
    if not path.exists():
        return {}
    book = load_workbook(path, read_only=True, data_only=True)
    result = {}
    for sheet in book:
        rows = iter(sheet.values)
        headers = [str(v) if v is not None else f"column_{i}" for i, v in enumerate(next(rows, []))]
        result[sheet.title] = [{k: native(v) for k, v in zip(headers, row)} for row in rows if any(v is not None for v in row)]
    book.close()
    return result


def point_rows(frame, sensor: str) -> list:
    rows = []
    for r in frame.to_dict("records"):
        rows.append([round(float(r["latitude"]), 5), round(float(r["longitude"]), 5), str(r["acq_date"]),
                     str(r["acq_time"]).zfill(4), "Aqua" if sensor == "modis" else "S-NPP",
                     "MODIS" if sensor == "modis" else "VIIRS", str(r["confidence"]),
                     round(float(r["frp"]), 2), str(r["daynight"]),
                     round(float(r.get("brightness") if sensor == "modis" else r.get("bright_ti4")), 2),
                     round(float(r["scan"]), 2), round(float(r["track"]), 2),
                     round(float(r.get("bright_t31") if sensor == "modis" else r.get("bright_ti5")), 2),
                     sensor == "synthetic", str(r.get("sim_source", "")),
                     str(r.get("sim_parent_modis", "")), int(r.get("sim_run", 0))])
    return rows


def build(results: Path, raw: Path, dest: Path, country="Malaysia", work: Path | None = None):
    import pandas as pd
    sys.path.insert(0, str(FINAL / "code"))
    import config
    config.COUNTRY, config.RAW, config.OUT = country, raw, results
    if work:
        config.WORK = work
    from sim_viirs import load_sensor, keep_representatives

    dest.mkdir(parents=True, exist_ok=True)
    calendar_path = results / f"calendar_2003_2020_{country}.csv"
    if not calendar_path.exists():
        raise FileNotFoundError(f"Missing completed burning calendar: {calendar_path}")
    calendar = pd.read_csv(calendar_path).to_dict("records")
    frames, dedupe = {}, {}
    for key, sensor, years in [("modis", "MODIS", range(2003, 2021)), ("viirs", "VIIRS", range(2012, 2021))]:
        cache = work / "sim_cache" / f"{key}.parquet" if work else None
        if cache and cache.exists():
            frames[key] = pd.read_parquet(cache)
        else:
            frames[key], dedupe[key] = keep_representatives(load_sensor(sensor, years))

    shards = []
    for year in range(2003, 2021):
        block = {}
        for key in ("modis", "viirs"):
            frame = frames[key]
            block[key] = point_rows(frame[frame["year"] == year], key)
        synthetic = results / "synthetic_viirs" / f"viirs-sim_{year}_{country}.csv"
        block["synthetic"] = point_rows(pd.read_csv(synthetic, dtype={"acq_time": str, "confidence": str}), "synthetic") if synthetic.exists() else []
        write_json(dest / "points" / f"{year}.json", block)
        shards.append({"year": year, "url": f"points/{year}.json", "counts": {k: len(v) for k, v in block.items()}})

    # Check the observed calendar against the actual cleaned point records before publishing.
    observed_counts = frames["viirs"].groupby(["year", "month"]).size().to_dict()
    for month in calendar:
        if month["source"].startswith("observed"):
            actual = observed_counts.get((month["year"], month["month"]), 0)
            if abs(month["value"] - actual) > 0.11:
                raise ValueError(f"Calendar/observation mismatch in {month['year']}-{month['month']}: {month['value']} vs {actual}")

    reports = {"loyo": workbook(results / f"loyo_{country.lower()}.xlsx"),
               "simulation": workbook(results / f"sim_eval_{country.lower()}.xlsx"),
               "handover": workbook(results / f"handover_{country.lower()}.xlsx"),
               "summary": workbook(FINAL / "results" / "RESULTS_SUMMARY.xlsx") if country == "Malaysia" else {}}
    write_json(dest / "reports.json", reports)
    downloads = []

    def include(path: Path, group: str, name: str | None = None):
        rel = Path("files") / group / (name or path.name)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        downloads.append({"name": name or path.name, "group": group, "url": rel.as_posix(), "bytes": target.stat().st_size,
                          "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})

    for path in sorted(results.glob("*.csv")):
        include(path, "calendar")
    for path in sorted(results.glob("*.xlsx")):
        include(path, "reports")
    for path in sorted(results.glob("*.json")):
        include(path, "reports")
    for path in sorted((results / "synthetic_viirs").glob("*.csv")):
        include(path, "synthetic")
    for path in sorted((results / "figures").glob("*.png")):
        include(path, "figures")
    for path in sorted((FINAL / "docs").glob("*")):
        if path.is_file():
            include(path, "documentation")
    include(FINAL / "results" / "README.md", "documentation", "Results_Guide.md")
    for path in sorted((FINAL / "results" / "extra").glob("*.xlsx")):
        include(path, "reports")

    source = dest / "files" / "source" / "harmonization-source.zip"
    source.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((FINAL / "code").rglob("*")):
            if path.is_file() and not any(p in {"__pycache__", "work", "output"} for p in path.relative_to(FINAL / "code").parts):
                archive.write(path, path.relative_to(FINAL / "code"))
    downloads.append({"name": "harmonization-source.zip", "group": "source", "url": "files/source/harmonization-source.zip", "bytes": source.stat().st_size,
                      "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    inputs = [{"file": p.relative_to(raw).as_posix(), "bytes": p.stat().st_size,
               "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in sorted(raw.rglob(f"*_{country}.csv"))]
    manifest = {"schema": 1, "country": country, "start": "2003-01-01", "end": "2020-12-31", "scale": "S-NPP VIIRS-equivalent detections",
                "method": "fusion_G1", "generated": datetime.now(timezone.utc).isoformat(), "columns": POINT_COLUMNS,
                "calendar": calendar, "shards": shards, "reports": "reports.json", "downloads": downloads,
                "inputs": inputs, "dedupe": dedupe,
                "notes": ["Synthetic points are simulations, not observed fires.", "January 2012 is partial and excluded from validation and the monthly baseline.",
                          "National estimated monthly totals use Fusion G1. Regional and day/night historical totals use synthetic run 1.",
                          "Accuracy applies to national monthly totals. Large fire years may be underestimated by 15–24%."]}
    write_json(dest / "manifest.json", manifest)
    print(f"Web bundle ready: {dest} ({sum(sum(s['counts'].values()) for s in shards):,} points)", flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=FINAL / "results")
    parser.add_argument("--raw", type=Path, default=FINAL / "code" / "data" / "raw")
    parser.add_argument("--dest", type=Path, default=ROOT / "frontend" / "public" / "data" / "final")
    parser.add_argument("--country", default="Malaysia")
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    build(args.results.resolve(), args.raw.resolve(), args.dest.resolve(), args.country, args.work.resolve() if args.work else None)
