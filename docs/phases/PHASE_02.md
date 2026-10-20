# PHASE 2 — Quality-aware Preprocessing (REVIEW PACK)

**Date:** 2026-10-20 | **Status:** Awaiting human decision (GATE 2). Not committed.

```
PHASE: 2, Quality-aware preprocessing
OBJECTIVE: Build a deterministic, versioned, auditable cleaning pipeline and compare missing-value / quality treatments.
DELIVERED: aquatic_xai/data/{clean,treatments}.py, aquatic_xai/reports/figures.py, configs/quality_rules.yaml,
           modal_jobs/phase2.py, tests/test_clean.py
MODAL RUNS: ap-RFvjv7rlw2t3zR9Wg9bxuU (tests, preprocess x2, analysis); ap-Rwlp55KVpZYCqOTZlYfPFf (temperature step check)
DATASET VERSION: pp-682986049e51 (raw commit 4cfa138e725d..., clean-v1); 17 ponds; 72,750 raw = 72,492 processed + 258 quarantined
TESTS: 12 passed, 0 failed, 0 skipped (remote). Idempotence: second Modal run reproduced identical content hashes for all 17 ponds.
METRICS: N/A (no models)
COST / RESOURCES: CPU only, seconds per job. Billing not visible from CLI; please confirm in the dashboard.
SCIENTIFIC CHECK: Nothing deleted: masked cells keep raw values; quarantined rows keep reasons. No future data used. See below.
GITHUB: research/init at a8a0de7 (Phase 1). Phase 2 NOT committed (awaiting approval).
DECISION REQUIRED: APPROVED / REJECTED / REQUEST CHANGES
NEXT PHASE (BLOCKED): Phase 3, causal feature engineering
```

## What the pipeline does
- Standardizes columns, parses IST timestamps (fixed UTC+05:30, no DST), adds `ts_utc`.
- Per cell status: `ok`, `zero_artifact`, `dup_conflict`, `out_of_bounds`, `null`. Working value is NaN when not `ok`; `<var>_raw` keeps the original.
- Duplicate timestamps: identical rows collapse; variables that differ are masked (`dup_conflict`); extra rows go to a quarantine table.
- QC flags are parsed into booleans (`flag_do_lt01`, `flag_do_jump`, `flag_ph_range`, ...) and **do not mask values**.
- Physical bounds are hard limits only (DO 0–30, pH 0–14, Temp 0–45): 0 cells were out of bounds.

## Decision table (pooled over 17 ponds; DO target; origins = lookback 6 h, valid target)

| Option | Valid DO / pH / Temp | DO<1.0 events kept | DO<0.1 events kept | Origins L24/h4 | Origins L24/h24 | Decision |
|---|---|---|---|---|---|---|
| T0 raw as-is | 72,492 each | 4,399 | 271 | 45,637 | 44,796 | Reject: zeros count as "events" |
| T1 zeros masked | 72,362 / 71,976 / 72,382 | 4,269 | 141 | 44,991 | 44,161 | Superseded by T2 |
| **T2 primary** (zeros + conflicting duplicates masked, flags kept) | 72,153 / 71,724 / 72,259 | 4,229 | 141 | 44,673 | 43,842 | **Recommended** |
| T3 drop all flagged values | 67,629 / 71,647 / 72,259 | 4,045 | **0** | 27,945 | 26,636 | Reject: deletes every near-zero DO event, loses 37% of origins |
| T4 T2 + causal ffill (<=2 steps) | same real values | 4,229 | 141 | 66,941 | 65,908 | Keep as an *ablation input treatment*, not as the dataset |

Reading it: T0's 271 "DO<0.1" events include 130 zero artifacts, so zeros nearly double the apparent hypoxia events (271 vs 141). T3's rule would remove every real near-zero DO reading, which is the most important kind of event. T4 raises usable origins by about 50% but fills with stale values (bounded to 30 min); targets always remain real observations. DO median 6.16 to 6.18 and p99 18.94 to 18.95 between T0 and T2, so masking barely changes the overall distribution but removes false extremes.

## Cell status after cleaning
| variable | ok | zero_artifact | dup_conflict |
|---|---|---|---|
| DO | 72,153 | 130 | 209 |
| pH | 71,724 | 516 | 252 |
| Temp | 72,259 | 110 | 123 |

Grid points with no row (outages): 6,499 per variable. Missingness is almost uniform by time of day (7.7%–9.0% per 4-hour block), so no strong diurnal bias.

## Calibration event (8–9 Jan)
- Median shift across the event (3 days before vs 3 days after, ponds with enough data), compared with ordinary shifts of the same size:
  - Temperature: about -2 °C in 15 of 16 ponds, above the 90th percentile of normal shifts.
  - DO: 2 of 16 ponds above the 90th percentile; pH: 3 of 16. Not systematic.
- **Follow-up (cross-pond daily mean temperature):** 26.4, 26.3, 26.1, 25.6, 24.8, 24.3, 24.1 °C for 5–11 Jan. It is a smooth six-day decline with the daytime cycle intact and **no step at the calibration time**. It looks like a common cold spell, not a sensor offset. This cannot prove there is no small calibration offset.
- Recommendation: treat 8–9 Jan as a documented event, do not use it as a split boundary, and keep a feature or flag for "days since calibration" as an optional Phase 3 ablation.

## Items kept for review (not removed)
- DO up to 25.6 mg/L (supersaturation, daytime), flagged `DO_>10_before_noon` where applicable.
- Temperature 36.0 °C (`b3d128ac`) and 33.5 °C (`45e1cde5`), both around 11:00–11:45 on 18 Jan in two different ponds. Unflagged by FWI; plausible warm-water episode or a probe issue. Kept.
- Chart for manual review: `/artifacts/reports/phase2/pp-682986049e51/plots/cleaning_audit.png` (ponds 3ed4df8e, ca187575, 3b2f3973). **I have not viewed this image**; it is generated but unchecked by me.

## Risks
- Zero masking relies on FWI's statement that zeros are artifacts; no independent evidence.
- Conflicting duplicates are masked, not resolved; true values unknown.
- T4 forward fill can hide stale readings from the model unless a mask/age feature accompanies it (planned in Phase 3).
- The temperature comparison is across only 16 ponds and one event; it does not isolate calibration from weather.
- Out-of-bounds rule is deliberately weak; sensor drift from probe fouling is not corrected.

## Guide explanation
1. We built a cleaning step that never throws data away: bad readings are marked and hidden from the model but kept for audit.
2. Machine-reset zeros and conflicting duplicate entries are masked, and each removed entry has a recorded reason.
3. We tested the alternative of deleting everything flagged and rejected it, because it would erase all genuine near-zero oxygen events.
4. Re-running the pipeline in a fresh cloud container gave identical dataset content (matching content hashes), so results are reproducible.
5. A suspected sensor recalibration turned out to look like ordinary cooling weather, so we did not split the data there.
