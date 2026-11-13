# PHASE 3 — Causal Feature Engineering (REVIEW PACK)

**Date:** 2026-10-20 | **Status:** Awaiting human decision (GATE 3). Not committed.

```
PHASE: 3, Causal feature engineering
OBJECTIVE: Build leakage-free features and targets for 15 min / 1 h / 6 h forecasts, with a dictionary and leakage tests on the real tables.
DELIVERED: aquatic_xai/features/{build,dictionary,leakage}.py, configs/features.yaml, modal_jobs/phase3.py,
           tests/test_features.py, docs/feature_dictionary.md
MODAL RUNS: ap-hAib9w5nYLRBLJR3057fFp (build; report step failed on missing scipy, my omission),
            ap-nEpKlwERE5jegKv25FKT8t (complete run with report)
DATASET VERSION: features ft-30c94e8fe1bd from processed pp-682986049e51; 17 ponds; 72,489 origins; 76 features; 9 targets
TESTS: 21 passed, 0 failed, 0 skipped (remote; 9 new feature tests + 12 earlier). Build re-run reproduced identical content hashes.
METRICS: N/A (no models trained)
COST / RESOURCES: CPU only, minutes in total. Billing not visible from the CLI; please check the dashboard.
SCIENTIFIC CHECK: 0 leakage mismatches in prefix test (680 origins) and 0 in target alignment (6,120 values). See below.
GITHUB: research/init at c1ada80 (Phase 2). Phase 3 NOT committed (awaiting approval).
DECISION REQUIRED: APPROVED / REJECTED / REQUEST CHANGES
NEXT PHASE (BLOCKED): Phase 4, temporal and unseen-pond split design
```

## Design
- **Origin:** a recorded row on the 15-minute grid (grid anchored at each pond's first reading, so some ponds have a 2-second offset; the grid-to-raw tolerance is 3 min and no row was off-grid). 3 raw rows that collided on the same grid slot were not placed (ponds 148f1633: 2, 29660d32: 1), so 72,492 processed rows give 72,489 origins.
- **Targets:** `y_{DO,pH,Temp}_h{1,4,24}` = the real valid reading 15 min / 1 h / 6 h later, else empty. No interpolation. 9 targets.
- **76 features** (full list with meaning, unit, window and validity in [docs/feature_dictionary.md](../feature_dictionary.md)):
  - history: current value and lags of 15 min, 30 min, 1, 2, 3, 6 h for DO, pH, Temp;
  - rolling: trailing mean/min/max/std over 1, 3, 6 h and a 3-hour slope;
  - quality: time since last valid reading, share valid in last 6 h, FWI flag now and counts in last 6 h, share of recorded time slots, gap since previous row;
  - time: sine/cosine of clock time (IST). Day-of-week and season were excluded because 7 weeks of data cannot support them.
- Warm-up origins (first 6 h of each pond, 404 in total) are kept but marked `is_warmup`; nothing is silently dropped.
- Pond ID is **not** a feature (unseen-pond generalization is a goal).

## Leakage and alignment tests (real tables, on Modal)
| Test | What it checks | Result |
|---|---|---|
| Prefix invariance | Recompute features after deleting all data after `t`; must equal the stored features | 680 origins, **0 mismatches**, max diff 0 |
| Target alignment | Re-derive targets by a separate timestamp lookup (not the grid shift) | 6,120 values, **0 mismatches** |
| Feature = target identity | No feature is a copy of a target | Max equal share 0.58 (`Temp_cur` vs `y_Temp_h1`) |
| Unit tests | Hand-computed lags, rolling stats, slope (exact), age, targets, future-change invariance, dictionary = built columns | 9/9 pass |

The 0.58 is not leakage: temperature is recorded to 0.1 °C and often unchanged over 15 minutes. It is what persistence would predict.

## Coverage (non-warm-up origins; pooled over 17 ponds)
| target | 15 min: valid target / + valid current / + >=80% valid last 6 h | 1 h | 6 h |
|---|---|---|---|
| DO | 70,093 / 70,062 / 67,699 | 69,622 / 69,544 / 67,205 | 68,432 / 68,308 / 66,003 |
| pH | 69,672 / 69,649 / 67,342 | 69,205 / 69,113 / 66,826 | 68,036 / 67,926 / 65,662 |
| Temp | 70,199 / 70,154 / 67,796 | 69,727 / 69,641 / 67,305 | 68,538 / 68,418 / 66,112 |

The 6-hour lag features have the most missing values (5–6%).

## Alignment examples (DO; independent raw lookups agree)
| pond | horizon | origin (IST) | DO now | lag 1 h (raw 60 min earlier) | target time | target (raw at target time) |
|---|---|---|---|---|---|---|
| 573a2826 | 15 min | 2026-01-07 11:00 | 4.74 | 3.28 (3.28) | 11:15 | 5.00 (5.00) |
| 573a2826 | 1 h | 2026-01-07 11:30 | 6.29 | 3.79 (3.79) | 12:30 | 10.84 (10.84) |
| 573a2826 | 6 h | 2026-01-07 11:00 | 4.74 | 3.28 (3.28) | 17:00 | 1.79 (1.79) |
| 3b2f3973 | 15 min / 1 h / 6 h | 2026-01-05 06:00, 07:00, 09:00 | 12.15, 11.85, 10.31 | match | +15 min, +1 h, +6 h | 12.08, 11.51, 19.27 (all match) |
| ca187575 | 15 min / 1 h / 6 h | 2026-01-05 11:00, 11:00, 07:30 | 3.49, 3.49, 0.45 | match | +15 min, +1 h, +6 h | 3.64, 3.46, 6.14 (all match) |

(Full table in the Modal report.)

## What the data say about feature sources (descriptive only)
|Spearman| on the first 50% of each pond's timeline, no model, **not used for selection**; train-only selection will be redone after the split freeze.
- **15 min to 1 h ahead:** the latest readings and short rolling means dominate (DO 0.94, pH 0.94, Temp 0.92). Persistence will be hard to beat at short horizons.
- **6 h ahead:** for DO and Temp the time of day (`hour_cos` 0.75 and 0.67) and trends/other variables overtake the latest value. This points to a strong daily cycle that a seasonal-naive baseline should capture. pH is still led by its current value (0.76).
- **Quality group:** weak by itself (best 0.06–0.36), but partly because FWI flags are rules on the value itself (for example "DO above 10 before noon"), so they can echo level information already present in the lags.

## Risks and caveats
1. Quality features may add little beyond the lags (flags are derived from values). Hypothesis H1 must be tested honestly and may fail.
2. The prefix test shows that features do not use the future; it does not prove that FWI's flag at time `t` could have been known in real time at `t`. Flags look backward by design (jump = change since previous reading, gap = since previous row), so I consider them causal, but I cannot verify how FWI created them.
3. Lag/rolling features use real observations only, so 4–6% are missing at long lags. LightGBM/XGBoost handle NaN natively; ridge/GRU need an imputation rule fitted on training rows only (to be defined in Phase 5).
4. The informativeness table is exploratory and used the first half of each pond, which will overlap the training region.
5. Features have not yet been exposed to any model or test set.

## Guide explanation
1. For every 15-minute moment we describe what the sensor "knew so far": recent readings, short-term averages and trends, and how reliable they were.
2. The answer we want to predict is a real reading 15 minutes, 1 hour or 6 hours later, and it is left empty if no such reading exists.
3. We proved the features cannot peek ahead by deleting all future data and rebuilding them, which gave exactly the same numbers.
4. We also checked 6,120 answers against the raw sensor files, and all matched.
5. Early look: for short forecasts the latest reading matters most, and for 6 hours ahead the time of day matters most.
