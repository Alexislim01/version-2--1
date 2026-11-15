"""Download NASA FIRMS country-year CSVs (Standard Processing, no login needed).

Files are kept only when their byte size matches the FIRMS index, so a
truncated download is never used. Existing complete files are skipped.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import config

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/data/country"
INDEX_URL = f"{BASE_URL}/yearly_summary_files.txt"
PRODUCTS = {"modis": config.EARLY_YEARS.start, "viirs-snpp": config.TRAIN_YEARS.start}


def read_index() -> dict[str, int]:
    with urllib.request.urlopen(INDEX_URL, timeout=120) as r:
        lines = r.read().decode("utf-8").splitlines()
    sizes = {}
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) >= 2 and parts[1].isdigit():
            sizes[parts[0]] = int(parts[1])
    return sizes


def wanted_files(country: str) -> list[tuple[str, str]]:
    out = []
    for year in range(config.EARLY_YEARS.start, config.TRAIN_YEARS.stop):
        out.append(("modis", f"modis_{year}_{country}.csv"))
    for year in config.TRAIN_YEARS:
        out.append(("viirs-snpp", f"viirs-snpp_{year}_{country}.csv"))
    return out


def download(country: str | None = None, raw: Path | None = None) -> None:
    country = country or config.COUNTRY
    raw = raw or config.RAW
    sizes = read_index()
    for product, name in wanted_files(country):
        dest = raw / product / name
        expected = sizes.get(name)
        if expected is None:
            print(f"not in FIRMS index (no fires that year?): {name}")
            continue
        if dest.exists() and dest.stat().st_size == expected:
            print(f"ok      {name}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        year = name.split("_")[1]
        url = f"{BASE_URL}/{product}/{year}/{name}"
        tmp = dest.with_suffix(".part")
        print(f"get     {url}")
        urllib.request.urlretrieve(url, tmp)
        if tmp.stat().st_size != expected:
            tmp.unlink()
            raise RuntimeError(f"size mismatch for {name}: expected {expected}")
        tmp.replace(dest)


if __name__ == "__main__":
    download()
