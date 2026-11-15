# results — latest test results (Malaysia, plus an Indonesia check)

Everything here was produced by `../code/run_all.py`. Numbers are **leave-one-year-out**: the model is trained on 8 of the 9 years 2012–2020 and tested on the 9th, which it never saw.

## Start here: `RESULTS_SUMMARY.xlsx`
One workbook with everything side by side.

| Sheet | What it shows |
|---|---|
| `README` | How the tests work, in 8 lines |
| `Malaysia_LOYO_by_year` | **Main table.** Monthly error (WAPE %) of 7 methods for each held-out year 2012–2020, plus the exam-year mean and the 9-year mean |
| `Malaysia_LOYO_other_metrics` | The same 7 methods with all other measures, for three groups of years (exam / tuning / all nine) |
| `Indonesia_LOYO_by_year`, `Indonesia_LOYO_other_metrics` | Same tests in Indonesia (5 methods) — does it hold in another country? |
| `Trees_200_vs_800` | Fusion G1 with 200 vs 800 trees (same result) |
| `Simulation_by_year_mean` | Point-level synthetic VIIRS test, per exam year, mean of 5 runs, vs a random-draw control |
| `Simulation_choice` | Simulation settings that were chosen on the tuning years |
| `Simulation_vs_fusion` | Synthetic point count vs Fusion G1 count (should agree within ~1%) |
| `Handover_out_of_sample` | Yearly totals, predicted (never-seen year) vs real S-NPP — shows big fire years are under-estimated |
| `Handover_sim_annual` | Synthetic yearly totals 2003–2014 (mean, min, max of 5 runs) |
| `Handover_handover` | 2012–2014 synthetic vs real, **in-sample** (model saw these years — reference only) |

## The 7 methods (rows in the LOYO sheets)

| Code | Name | What it does |
|---|---|---|
| `raw` | No conversion | Use MODIS counts as they are |
| `daynight_k` | Day/night multiplier | MODIS × (VIIRS ÷ MODIS), one number for day, one for night |
| `strat_k` | Stratified multiplier | Same, but per 1° area × calendar month × day/night, smoothed |
| `fusion` | Fusion (original) | Day/night multiplier + random forest that corrects the rest; may add fires in cells where MODIS saw none |
| **`fusion_G1`** | **Fusion G1 — chosen** | Like `fusion`, but adds fires to an empty cell **only if** fire was seen next to it or at the other time of day |
| `fusion_G2` | Fusion G2 | Separate model decides whether an empty cell has fire, then how much |
| `fusion_G3` | Fusion G3 | Background in empty cells re-scaled on a validation year |

## What each value means

| Column | Meaning | Good value |
|---|---|---|
| `month_wape` | **Main score.** Monthly national error = Σ\|predicted − actual\| ÷ Σ actual × 100, over the 12 months of the held-out year (day + night summed) | Lower; 0 = perfect |
| `2012*` … `2020` | `month_wape` for that held-out year. `2012*` = without January (S-NPP starts 20 Jan 2012) | Lower |
| `exam_mean` | Mean of 2012*, 2019, 2020 — the exam years fixed **before** testing; used to choose the method | Lower |
| `nine_year_mean` | Mean of all nine held-out years — the most stable summary | Lower |
| `year_abs_pct` | Error in the yearly total, % | Lower |
| `month_r` | Correlation between predicted and real monthly totals | Closer to 1 |
| `peak_hit` | Share of years where the busiest fire month was predicted correctly | 1 = always |
| `anomaly_sign_pct` | % of months where "above / below the usual level" was called correctly | Higher |
| `interannual_ratio` | Spread of predicted yearly totals ÷ spread of real ones. <1 = years look too similar; >1 = differences exaggerated | Closer to 1 |
| `cell_mae` | Average error per 0.25° cell per month (detections) | Lower |
| `frp_month_wape` | Same as `month_wape` but for total fire radiative power | Lower |
| `actual_sum`, `pred_sum` | Real and predicted detections in the held-out year | — |
| `slice` | Which years are averaged: exam / tuning (2013–2018) / all nine | — |

**Simulation columns** (`Simulation_*`, `sim_eval_malaysia.xlsx`)

| Column | Meaning |
|---|---|
| `n_sim`, `n_actual` | Synthetic vs real VIIRS detections in that year |
| `n_paired`, `n_hole` | Synthetic points copied from a MODIS detection's matched VIIRS group / added where MODIS saw nothing |
| `month_wape`, `year_abs_pct` | As above, for the synthetic points |
| `control_…` | Same measure for the **control**: the same number of real VIIRS points drawn at random from the same month of the training years |
| `cell_mae`, `cell_r` | Error and correlation of counts per 0.25° cell per month (location skill) |
| `*_w1` | Wasserstein distance between synthetic and real distributions of that column (FRP, bright_ti4, bright_ti5, scan, track) — lower = more alike |
| `*_ks` | Kolmogorov–Smirnov statistic, same idea |
| `confidence_tv`, `hour_tv` | Difference in the share of each confidence class / hour of day (0 = identical) |
| `daynight_abs` | Difference in the night share |
| `better_…` | True if the synthetic points beat the control on that measure |
| `paired_precision` / `paired_recall` | Share of synthetic (paired) points with a real VIIRS point within 1 km on the same day / share of real points with a synthetic one nearby |
| `hole_precision` / `hole_recall`, `control_precision` / `control_recall` | Same, for hole points and for the control |
| `K`, `alpha`, `jitter_km` | Simulation settings (neighbours searched, FRP scaling, position jitter) |
| `capped`, `holes_missed` | Book-keeping: points removed by the per-cell cap / hole points that could not be placed |

**Handover columns**: `actual` = real S-NPP detections; `fusion_G1_loyo` = predicted by a model that never saw that year; `signed_gap_pct` = (predicted − actual) ÷ actual × 100 (negative = under-estimate); `sim_mean/min/max/run1` = synthetic totals across the 5 runs.

## Other files

| File | What it is |
|---|---|
| `loyo_malaysia.xlsx` | Raw output of the leave-one-year-out step: `by_year`, `averages`, `choice` (chosen method and the rule used) |
| `sim_eval_malaysia.xlsx` | Raw output of the simulation test: `by_run` (15 runs), `by_year_mean`, `choice`, `vs_fusion`, `notes`, `tune` (36 settings tried on 2013–2018) |
| `handover_malaysia.xlsx` | Yearly totals: `out_of_sample`, `handover` (in-sample), `sim_annual`, `actual_2012_2020`, `runs` |
| `calendar_2003_2020_Malaysia.csv` | **The burning calendar.** One row per month: `value` = S-NPP-equivalent detections; `source` = `estimated` (2003–2011, from MODIS) / `observed` / `observed_partial` (Jan 2012); `median` = median of that calendar month over 2003–2020; `anomaly_pct` = (value − median) ÷ median × 100 |
| `synthetic_viirs/viirs-sim_{year}_Malaysia.csv` | **Synthetic VIIRS detections, 2003–2011**, one file per year. Same 15 columns as a FIRMS VIIRS CSV, plus `is_synthetic`, `sim_source` (`paired`/`hole`), `sim_parent_modis` (year:row of the MODIS detection it came from), `sim_run`. `version = SIM1.0`. A simulation, not observations |
| `synthetic_viirs/sim_runs_summary.csv` | Point counts of each of the 5 runs per year |
| `figures/` | `annual_timeline_2003_2020.png` (yearly totals), `map_2019_m03.png` (real vs synthetic map), `param_*.png` (distribution of each column: real / synthetic / control), `website_check.png` (calendar web page) |
| `extra/` | Inputs for the summary that come from earlier runs: Indonesia leave-one-year-out, Malaysia 800-tree check |

## Headline (Malaysia, Fusion G1)
Monthly error **17.1%** over nine never-seen years (15.5% on the exam years), down from **84.8%** without conversion. Indonesia: 15.3% vs 86.4%. Large fire years are under-estimated by about 15–24%.
