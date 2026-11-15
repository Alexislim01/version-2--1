"""Pairing v2: footprint + fixed-1km MODIS/VIIRS candidate pairs (Indonesia 2023).

Candidate pair = same-time/same-place hypothesis only. Not proof of one fire.
Does not compute k. Writes under pipeline_v2/output/pairing/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Geod, Transformer
from scipy.spatial import cKDTree

METHOD_VERSION = "pair-v2-1.0"
OBS_DEFAULT = Path(
    r"C:\Users\User\Downloads\NASA\testing_indonesia\stage1_observations\data\observations.csv.gz"
)
OUT_DEFAULT = Path(__file__).resolve().parent / "work" / "pairing"
GEOD = Geod(ellps="WGS84")
_TO_6933 = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
TIERS = {"strict": 5, "medium": 30, "loose": 90}
FOOTPRINT_COARSE_M = 3100.0  # 0.5*(4.8+0.8)*1.1 km before index pad
# EPSG:6933 stretches N-S near the equator (~1.155x); pad k-d search by 1.25 so
# true geodesic neighbours are not dropped before the exact filter.
KD_PAD = 1.25
COLS = [
    "record_id", "sensor", "satellite", "latitude_deg", "longitude_deg",
    "acquired_at_utc", "scan_km", "track_km", "frp_mw",
    "modis_confidence_score", "viirs_confidence_category",
    "daynight", "hotspot_type", "alignment_eligible",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def conf_bin_modis(score: str) -> str:
    if score.strip() == "":
        return ""
    try:
        v = float(score)
    except ValueError:
        return ""
    if v < 30:
        return "low"
    if v < 80:
        return "nominal"
    return "high"


def load_observations(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=lambda c: c in COLS)
    miss = [c for c in COLS if c not in df.columns]
    if miss:
        raise ValueError(f"missing columns: {miss}")
    df = df[df["alignment_eligible"].str.lower() == "true"].copy()
    df = df[df["satellite"].isin(["Aqua", "SNPP"])].copy()
    df["lat"] = pd.to_numeric(df["latitude_deg"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude_deg"], errors="coerce")
    df["scan"] = pd.to_numeric(df["scan_km"], errors="coerce")
    df["track"] = pd.to_numeric(df["track_km"], errors="coerce")
    df["frp"] = pd.to_numeric(df["frp_mw"], errors="coerce")
    t = pd.to_datetime(df["acquired_at_utc"], format="%Y-%m-%dT%H:%M:%SZ", utc=True, errors="coerce")
    df["tmin"] = ((t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds() // 60).astype("Int64")
    df = df.dropna(subset=["lat", "lon", "tmin"]).copy()
    df["tmin"] = df["tmin"].astype(np.int64)
    df["day"] = df["tmin"] // 1440
    df["x"], df["y"] = _TO_6933.transform(df["lon"].to_numpy(), df["lat"].to_numpy())
    df["conf_bin"] = np.where(
        df["sensor"] == "MODIS",
        df["modis_confidence_score"].map(conf_bin_modis),
        df["viirs_confidence_category"].str.lower().str.strip(),
    )
    return df.reset_index(drop=True)


def apply_filters(
    df: pd.DataFrame,
    *,
    filter_type0: bool = True,
    filter_confidence: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return filtered frame + filter_log rows."""
    rows = []
    cur = df
    rows.append(_filter_row("start", cur))
    if filter_type0:
        cur = cur[cur["hotspot_type"] == "0"].copy()
        rows.append(_filter_row("hotspot_type_eq_0", cur))
    if filter_confidence:
        cur = cur[cur["conf_bin"].isin(["nominal", "high"])].copy()
        rows.append(_filter_row("confidence_nominal_high", cur))
    return cur.reset_index(drop=True), pd.DataFrame(rows)


def _filter_row(step: str, df: pd.DataFrame) -> dict:
    return {
        "step": step,
        "n_total": len(df),
        "n_modis": int((df["sensor"] == "MODIS").sum()),
        "n_viirs": int((df["sensor"] == "VIIRS").sum()),
    }


def mark_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Mark same-sensor same-minute footprint-overlap duplicates; keep max FRP as representative."""
    out = df.copy()
    out["dup_of"] = ""
    out["is_representative"] = True
    parent = {i: i for i in out.index}

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    n_dup_links = 0
    for (sensor, tmin), g in out.groupby(["sensor", "tmin"], sort=False):
        if len(g) < 2:
            continue
        idx = g.index.to_numpy()
        lat = g["lat"].to_numpy()
        lon = g["lon"].to_numpy()
        scan = g["scan"].to_numpy()
        track = g["track"].to_numpy()
        # coarse neighbours in projected metres (~ half max scan)
        xy = np.column_stack([g["x"].to_numpy(), g["y"].to_numpy()])
        tree = cKDTree(xy)
        for i in range(len(idx)):
            js = tree.query_ball_point(xy[i], r=5000.0)
            for j in js:
                if j <= i:
                    continue
                sc = min(scan[i], scan[j])
                tr = min(track[i], track[j])
                if not (sc > 0 and tr > 0):
                    continue
                dx = abs(lon[i] - lon[j]) * 111.32 * math.cos(math.radians(lat[i]))
                dy = abs(lat[i] - lat[j]) * 110.57
                overlap = max(0.0, 1.0 - dx / sc) * max(0.0, 1.0 - dy / tr)
                if overlap > 0.3:
                    union(int(idx[i]), int(idx[j]))
                    n_dup_links += 1

    # choose representative per component
    comps: dict[int, list[int]] = {}
    for i in out.index:
        comps.setdefault(find(int(i)), []).append(int(i))

    n_marked = 0
    for members in comps.values():
        if len(members) < 2:
            continue
        frps = out.loc[members, "frp"].fillna(-np.inf)
        rep = int(frps.idxmax())
        for m in members:
            if m == rep:
                out.at[m, "dup_of"] = ""
                out.at[m, "is_representative"] = True
            else:
                out.at[m, "dup_of"] = out.at[rep, "record_id"]
                out.at[m, "is_representative"] = False
                n_marked += 1

    summary = {
        "n_points": len(out),
        "n_duplicate_marked": n_marked,
        "n_components_with_dups": sum(1 for m in comps.values() if len(m) > 1),
        "n_overlap_links": n_dup_links,
        "dup_pct": round(100.0 * n_marked / len(out), 1) if len(out) else 0.0,
        "dup_pct_modis": _dup_pct(out, "MODIS"),
        "dup_pct_viirs": _dup_pct(out, "VIIRS"),
    }
    return out, summary


def _dup_pct(df: pd.DataFrame, sensor: str) -> float:
    sub = df[df["sensor"] == sensor]
    if sub.empty:
        return 0.0
    return round(100.0 * (~sub["is_representative"]).sum() / len(sub), 1)


def geodesic_m(lon1, lat1, lon2, lat2) -> np.ndarray:
    _, _, d = GEOD.inv(
        np.asarray(lon1, float), np.asarray(lat1, float),
        np.asarray(lon2, float), np.asarray(lat2, float),
    )
    return np.asarray(d, dtype=float)


def pair_candidates(
    df: pd.DataFrame,
    window_min: int,
    *,
    radius_m: float,
    viirs_tmin_shift: int = 0,
    use_representatives_only: bool = True,
) -> pd.DataFrame:
    """Many-to-many MODIS-VIIRS pairs within radius_m geodesic and |dt|<=window_min.

    Returns columns including dx_km, dy_km for footprint filtering downstream.
    """
    m = df[df["sensor"] == "MODIS"]
    v = df[df["sensor"] == "VIIRS"]
    if use_representatives_only:
        m = m[m["is_representative"]]
        v = v[v["is_representative"]]
    if m.empty or v.empty:
        return pd.DataFrame(columns=[
            "modis_record_id", "viirs_record_id", "distance_m", "dx_km", "dy_km",
            "dt_min", "daynight", "modis_scan", "modis_track", "viirs_scan", "viirs_track",
        ])

    v = v.copy()
    if viirs_tmin_shift:
        v["tmin"] = v["tmin"] + viirs_tmin_shift
        v["day"] = v["tmin"] // 1440

    v_by_day = {d: g for d, g in v.groupby("day")}
    span = math.ceil(window_min / 1440) if window_min else 0
    rows = []
    for day, mg in m.groupby("day"):
        parts = [
            v_by_day[d]
            for d in range(day - span - (1 if window_min else 0), day + span + 2)
            if d in v_by_day
        ]
        if not parts:
            continue
        vg = pd.concat(parts)
        t0, t1 = int(mg["tmin"].min()) - window_min, int(mg["tmin"].max()) + window_min
        vg = vg[(vg["tmin"] >= t0) & (vg["tmin"] <= t1)]
        if vg.empty:
            continue
        tree = cKDTree(vg[["x", "y"]].to_numpy())
        hits = tree.query_ball_point(mg[["x", "y"]].to_numpy(), r=radius_m * KD_PAD)
        vt = vg["tmin"].to_numpy()
        vlon = vg["lon"].to_numpy()
        vlat = vg["lat"].to_numpy()
        vscan = vg["scan"].to_numpy()
        vtrack = vg["track"].to_numpy()
        vids = vg["record_id"].to_numpy()
        for i, js in enumerate(hits):
            if not js:
                continue
            js = np.asarray(js, dtype=np.int64)
            dt = vt[js] - int(mg["tmin"].iat[i])
            keep = np.abs(dt) <= window_min
            if not keep.any():
                continue
            js, dt = js[keep], dt[keep]
            mlat = float(mg["lat"].iat[i])
            mlon = float(mg["lon"].iat[i])
            # Keep full-precision geodesic metres for the exact filter (do not round first).
            d = geodesic_m(np.full(len(js), mlon), np.full(len(js), mlat), vlon[js], vlat[js])
            ok = d <= radius_m
            js, dt, d = js[ok], dt[ok], d[ok]
            if len(js) == 0:
                continue
            coslat = math.cos(math.radians(mlat))
            dx = np.abs(vlon[js] - mlon) * 111.32 * coslat
            dy = np.abs(vlat[js] - mlat) * 110.57
            mid = mg["record_id"].iat[i]
            mdn = mg["daynight"].iat[i]
            msc = float(mg["scan"].iat[i])
            mtr = float(mg["track"].iat[i])
            for j, dd, tt, ddx, ddy in zip(js, d, dt, dx, dy):
                rows.append((
                    mid, vids[j], float(dd), float(ddx), float(ddy),
                    int(tt), mdn, msc, mtr, float(vscan[j]), float(vtrack[j]),
                ))
    cols = [
        "modis_record_id", "viirs_record_id", "distance_m", "dx_km", "dy_km",
        "dt_min", "daynight", "modis_scan", "modis_track", "viirs_scan", "viirs_track",
    ]
    return pd.DataFrame(rows, columns=cols)


def apply_rule(cands: pd.DataFrame, rule: str) -> pd.DataFrame:
    if cands.empty:
        return cands.iloc[0:0].copy()
    if rule == "fixed1km":
        # Compare unrounded geodesic metres (rounding 1000.04 -> 1000.0 would falsely keep).
        keep = cands["distance_m"] <= 1000.0
    elif rule == "footprint":
        keep = (
            (cands["dx_km"] <= (cands["modis_scan"] + cands["viirs_scan"]) / 2.0)
            & (cands["dy_km"] <= (cands["modis_track"] + cands["viirs_track"]) / 2.0)
        )
    else:
        raise ValueError(rule)
    out = cands.loc[keep].copy()
    out["rule"] = rule
    return out


def format_pairs_for_write(pairs: pd.DataFrame) -> pd.DataFrame:
    """Round display fields only after exact filters have been applied."""
    out = pairs.copy()
    if len(out):
        out["distance_m"] = out["distance_m"].round(1)
        out["dx_km"] = out["dx_km"].round(4)
        out["dy_km"] = out["dy_km"].round(4)
    return out


def summarise_pairs(
    pairs: pd.DataFrame,
    modis: pd.DataFrame,
    viirs: pd.DataFrame,
    *,
    rule: str,
    tier: str,
    daynight: str,
    null_mean_pct: float | None = None,
) -> dict:
    if daynight == "all":
        m = modis
        p = pairs
    else:
        m = modis[modis["daynight"] == daynight]
        p = pairs[pairs["daynight"] == daynight] if len(pairs) else pairs
    n_m = len(m)
    n_v = len(viirs) if daynight == "all" else len(viirs[viirs["daynight"] == daynight])
    # For daynight splits, VIIRS count by own daynight is reported for transparency;
    # pairing itself keys off MODIS daynight.
    if daynight != "all":
        n_v = len(viirs)  # keep full VIIRS pool size used in search when reporting? Plan wants n_viirs in pool.
        # Use representatives in the working set for that sensor with that daynight label on VIIRS side for n_viirs.
        n_v = int((viirs["daynight"] == daynight).sum())
    per_m = p.groupby("modis_record_id").size() if len(p) else pd.Series(dtype=int)
    per_v = p.groupby("viirs_record_id").size() if len(p) else pd.Series(dtype=int)
    matched_pct = round(100.0 * len(per_m) / n_m, 1) if n_m else 0.0
    row = {
        "rule": rule,
        "tier": tier,
        "daynight": daynight,
        "n_modis": n_m,
        "n_viirs": n_v,
        "pairs": int(len(p)),
        "modis_matched_pct": matched_pct,
        "viirs_matched_pct": round(100.0 * len(per_v) / n_v, 1) if n_v else 0.0,
        "viirs_per_matched_modis": round(float(per_m.mean()), 1) if len(per_m) else 0.0,
        "median_distance_m": round(float(p["distance_m"].median()), 1) if len(p) else None,
        "null_mean_pct": None if null_mean_pct is None else round(float(null_mean_pct), 1),
        "excess_pct": None if null_mean_pct is None else round(matched_pct - float(null_mean_pct), 1),
    }
    return row


def run_pairing_suite(
    df: pd.DataFrame,
    *,
    use_representatives_only: bool = True,
    tiers: dict[str, int] | None = None,
    do_null: bool = True,
    write_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Run footprint + fixed1km for each tier; optional null shifts; optional pair file writes."""
    tiers = tiers or TIERS
    work = df
    modis = work[(work["sensor"] == "MODIS") & (work["is_representative"] if use_representatives_only else True)]
    viirs = work[(work["sensor"] == "VIIRS") & (work["is_representative"] if use_representatives_only else True)]
    # if not use_representatives, is_representative may still exist; use all
    if not use_representatives_only:
        modis = work[work["sensor"] == "MODIS"]
        viirs = work[work["sensor"] == "VIIRS"]

    summary_rows = []
    pair_tables: dict[str, pd.DataFrame] = {}
    shifts = [-2, -1, 1, 2] if do_null else []

    for tier, window in tiers.items():
        t0 = time.time()
        cands = pair_candidates(
            work, window, radius_m=FOOTPRINT_COARSE_M,
            use_representatives_only=use_representatives_only,
        )
        print(f"  coarse {tier} ({window} min): {len(cands):,} candidates in {time.time()-t0:.1f}s")

        # Null shifts once per tier; both rules reuse the same coarse candidates.
        null_by_rule_dn: dict[str, dict[str, list[float]]] = {
            "footprint": {"all": [], "D": [], "N": []},
            "fixed1km": {"all": [], "D": [], "N": []},
        }
        if do_null:
            for sh in shifts:
                t_n = time.time()
                nc = pair_candidates(
                    work, window, radius_m=FOOTPRINT_COARSE_M,
                    viirs_tmin_shift=sh * 1440,
                    use_representatives_only=use_representatives_only,
                )
                print(f"  null shift {sh:+d}d: {len(nc):,} coarse in {time.time()-t_n:.1f}s")
                for rule in ("footprint", "fixed1km"):
                    npairs = apply_rule(nc, rule)
                    for dn in ("all", "D", "N"):
                        srow = summarise_pairs(
                            npairs, modis, viirs, rule=rule, tier=tier, daynight=dn,
                        )
                        null_by_rule_dn[rule][dn].append(srow["modis_matched_pct"])

        for rule in ("footprint", "fixed1km"):
            pairs = apply_rule(cands, rule)
            pairs["tier"] = tier
            key = f"{rule}_{tier}"
            pair_tables[key] = pairs[[
                "modis_record_id", "viirs_record_id", "distance_m", "dx_km", "dy_km",
                "dt_min", "daynight", "rule", "tier",
            ]].copy()
            if write_dir is not None:
                path = write_dir / f"pairs_{rule}_{tier}.csv.gz"
                format_pairs_for_write(pair_tables[key]).to_csv(
                    path, index=False, compression="gzip"
                )
            for dn in ("all", "D", "N"):
                null_mean = (
                    float(np.mean(null_by_rule_dn[rule][dn])) if do_null else None
                )
                summary_rows.append(
                    summarise_pairs(
                        pairs, modis, viirs, rule=rule, tier=tier, daynight=dn,
                        null_mean_pct=null_mean,
                    )
                )
    return pd.DataFrame(summary_rows), pair_tables


def regression_fixed1km(
    df_all: pd.DataFrame,
    window_min: int,
    *,
    hotspot_types: set[str] | None = None,
) -> tuple[int, int]:
    """Match stage2-style pairing: no confidence filter, no dedup, fixed 1 km."""
    cur = df_all.copy()
    cur["is_representative"] = True
    cur["dup_of"] = ""
    if hotspot_types is not None:
        cur = cur[cur["hotspot_type"].isin(hotspot_types)].copy()
    pairs = pair_candidates(cur, window_min, radius_m=1000.0, use_representatives_only=False)
    pairs = apply_rule(pairs, "fixed1km")
    n_pairs = len(pairs)
    n_matched = pairs["modis_record_id"].nunique() if n_pairs else 0
    return n_pairs, int(n_matched)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--obs", type=Path, default=OBS_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--no-type0", action="store_true")
    ap.add_argument("--no-confidence", action="store_true")
    ap.add_argument("--no-dedup", action="store_true", help="keep all points (still mark dups)")
    ap.add_argument("--skip-null", action="store_true")
    ap.add_argument("--tiers", default="strict,medium,loose")
    ap.add_argument("--regression-only", action="store_true")
    args = ap.parse_args(argv)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    obs_sha = sha256_file(args.obs)
    print(f"Loading {args.obs} ...")
    raw = load_observations(args.obs)
    print(f"  eligible Aqua/SNPP rows: {len(raw):,}")

    if args.regression_only:
        p1, m1 = regression_fixed1km(raw, 60, hotspot_types=None)
        p2, m2 = regression_fixed1km(raw, 90, hotspot_types={"0"})
        print(f"REG1 all-types 1km/60: pairs={p1} matched_modis={m1} (expect 43797 / 15376)")
        print(f"REG2 type0 1km/90: pairs={p2} matched_modis={m2} (expect 47118)")
        ok = (p1 == 43797 and m1 == 15376 and p2 == 47118)
        return 0 if ok else 1

    filtered, filter_log = apply_filters(
        raw,
        filter_type0=not args.no_type0,
        filter_confidence=not args.no_confidence,
    )
    marked, dup_summary = mark_duplicates(filtered)
    print(f"After filters: {len(marked):,}  dup_pct={dup_summary['dup_pct']}%")
    if dup_summary["dup_pct"] > 10.0:
        blocked = Path(__file__).resolve().parent / "work" / "BLOCKED.md"
        blocked.write_text(
            f"# BLOCKED\n\nDuplicate rate {dup_summary['dup_pct']}% > 10%.\n\n"
            f"Summary: {json.dumps(dup_summary, ensure_ascii=False, indent=2)}\n",
            encoding="utf-8",
        )
        print("BLOCKED: duplicate rate > 10%. See BLOCKED.md")
        return 2

    use_rep = not args.no_dedup
    tier_names = [t.strip() for t in args.tiers.split(",") if t.strip()]
    tiers = {t: TIERS[t] for t in tier_names}
    print("Pairing suite...")
    summary, tables = run_pairing_suite(
        marked,
        use_representatives_only=use_rep,
        tiers=tiers,
        do_null=not args.skip_null,
        write_dir=out,
    )
    filter_log.to_csv(out / "filter_log.csv", index=False)
    pd.DataFrame([dup_summary]).to_csv(out / "duplicates_summary.csv", index=False)
    # also write per-record dup flags for audit
    marked[["record_id", "sensor", "dup_of", "is_representative"]].to_csv(
        out / "duplicate_flags.csv.gz", index=False, compression="gzip"
    )
    summary.to_csv(out / "pairing_summary.csv", index=False)

    # stop condition: main setting excess_pct <= 0
    main = summary[
        (summary["rule"] == "footprint")
        & (summary["tier"] == "strict")
        & (summary["daynight"] == "all")
    ]
    if len(main) and main.iloc[0]["excess_pct"] is not None and main.iloc[0]["excess_pct"] <= 0:
        blocked = Path(__file__).resolve().parent / "work" / "BLOCKED.md"
        blocked.write_text(
            "# BLOCKED\n\nMain setting footprint x strict x all has excess_pct <= 0.\n\n"
            f"{main.to_string(index=False)}\n",
            encoding="utf-8",
        )
        print("BLOCKED: main excess_pct <= 0")
        return 3

    # flag other excess <= 0 in a side file (continue)
    bad = summary[summary["excess_pct"].notna() & (summary["excess_pct"] <= 0)]
    if len(bad):
        bad.to_csv(out / "excess_nonpositive_flags.csv", index=False)
        print(f"WARNING: {len(bad)} settings with excess_pct <= 0 (non-main); flagged.")

    meta = {
        "method_version": METHOD_VERSION,
        "obs_path": str(args.obs),
        "obs_sha256": obs_sha,
        "filters": {
            "type0": not args.no_type0,
            "confidence_nominal_high": not args.no_confidence,
            "use_representatives_only": use_rep,
        },
        "tiers_min": tiers,
        "null_shifts_days": [-2, -1, 1, 2] if not args.skip_null else [],
        "duplicates": dup_summary,
        "n_pair_tables": len(tables),
    }
    (out / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Done. pairing_summary.csv written.")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
