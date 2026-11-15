"""Burning calendar: one row per year x month, on the S-NPP VIIRS scale.

2003-2011: Fusion G1 estimate from Aqua MODIS (model trained on all 2012-2020).
2012-2020: observed S-NPP vegetation-fire detections (cleaned, de-duplicated).
Median and anomaly use every year 2003-2020 for the same calendar month.
"""
from __future__ import annotations

import pandas as pd

import config


def build() -> pd.DataFrame:
    p = config.paths()
    early = pd.read_csv(p["cache"] / "early_monthly.csv")
    early = early.rename(columns={"pred": "value"})
    early["source"] = "estimated"
    viirs = pd.read_parquet(p["cache"] / "viirs.parquet")
    obs = viirs.groupby(["year", "month"]).size().rename("value").reset_index()
    obs["source"] = "observed"
    obs.loc[(obs["year"] == 2012) & (obs["month"] == 1), "source"] = "observed_partial"
    cal = pd.concat([early, obs], ignore_index=True)
    full = pd.MultiIndex.from_product(
        [range(config.EARLY_YEARS.start, config.TRAIN_YEARS.stop), range(1, 13)], names=["year", "month"]
    ).to_frame(index=False)
    cal = full.merge(cal, on=["year", "month"], how="left")
    cal["value"] = cal["value"].fillna(0.0).round(1)
    cal["source"] = cal["source"].fillna("estimated")
    base = cal[cal["source"] != "observed_partial"]
    med = base.groupby("month")["value"].median().rename("median")
    cal = cal.merge(med, on="month")
    cal["median"] = cal["median"].round(1)
    cal["anomaly_pct"] = ((cal["value"] - cal["median"]) / cal["median"].clip(lower=1) * 100).round(1)
    cal = cal.sort_values(["year", "month"]).reset_index(drop=True)
    out = config.OUT / f"calendar_{config.EARLY_YEARS.start}_{config.TRAIN_YEARS.stop - 1}_{config.COUNTRY}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cal.to_csv(out, index=False)
    print(f"wrote {out}")
    return cal


if __name__ == "__main__":
    build()
