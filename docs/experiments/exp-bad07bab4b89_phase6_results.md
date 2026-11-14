# Phase 6 results, experiment `exp-bad07bab4b89`

- Split `sp-2dd59e32cff4` (unchanged), features `ft-30c94e8fe1bd` + daily-v1, code commit `b22fb95-unco`. Validation-side only; sealed test not used.
- Contract: `configs/phase6.yaml` (written before running). One round, no tuning.

## A. Forecast ranges (split-conformal), unseen ponds

Target: the range contains the truth 90% of the time. Calibration = errors on the other three pond groups (disjoint ponds). Centre of each range = the Phase 5b recommended predictor for that cell. Coverage intervals are 95% blocked-bootstrap.

| target | ahead | centre | coverage (plain) | width plain | width if centred on 'same as now' | day / night / low-value coverage | coverage (day/night variant) | day / night / low | per-fold coverage (min-max) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| DO (mg/L) | 15 min | anch_blind | 89.9% [88.5, 91.3] | ±1.105 | ±1.130 | 85% / 95% / 97% | 90.0% | 90% / 90% / 97% | 84%-93% | PASS (plain) |
| DO (mg/L) | 1 h | anch_blind | 89.9% [88.4, 91.3] | ±2.151 | ±2.768 | 84% / 96% / 97% | 89.8% | 90% / 90% / 97% | 85%-94% | PASS (day/night) |
| DO (mg/L) | 6 h | anch_blind | 89.9% [87.5, 92.0] | ±3.991 | ±9.690 | 82% / 98% / 96% | 89.8% | 90% / 90% / 90% | 84%-95% | PASS (day/night) |
| pH (pH units) | 15 min | persistence | 89.7% [84.7, 94.1] | ±0.067 | ±0.067 | 89% / 90% / 95% | 89.6% | 90% / 89% / 94% | 62%-100% | PASS (plain) |
| pH (pH units) | 1 h | persistence | 88.9% [84.7, 93.0] | ±0.105 | ±0.105 | 87% / 91% / 95% | 89.6% | 89% / 90% / 95% | 64%-99% | PASS (plain) |
| pH (pH units) | 6 h | seasonal_naive | 89.1% [84.7, 93.0] | ±0.170 | ±0.280 | 89% / 89% / 92% | 89.2% | 89% / 89% / 92% | 71%-98% | PASS (plain) |
| Temp (°C) | 15 min | persistence | 89.5% [84.3, 93.7] | ±0.268 | ±0.268 | 87% / 92% / 94% | 91.0% | 90% / 92% / 94% | 65%-99% | PASS (plain) |
| Temp (°C) | 1 h | anch_blind | 89.1% [85.2, 92.5] | ±0.477 | ±0.580 | 85% / 94% / 95% | 89.3% | 90% / 89% / 93% | 71%-98% | PASS (day/night) |
| Temp (°C) | 6 h | anch_blind | 89.6% [87.1, 91.9] | ±0.894 | ±1.850 | 84% / 95% / 95% | 89.5% | 90% / 89% / 91% | 80%-95% | PASS (day/night) |

**9 of 9 cells pass** the pre-registered coverage rule (pooled coverage on unseen ponds in [0.87, 0.93] for the plain variant; conditional check: coverage >= 0.85 in day, night and low-value strata, else the app uses the day/night variant).

## B. Low-oxygen early warning (event = any reading below 2.0 mg/L within the next window), unseen ponds

Average precision (AP; 1.0 is perfect, the event rate is the no-skill level). Higher is better.

| window | event rate | model | 'same window yesterday' | 'trend' | 'current level' | model minus each baseline (99% interval) | verdict |
|---|---|---|---|---|---|---|---|
| 1h | 17.1% | 0.945 | 0.578 | 0.923 | 0.937 | vs yesterday: +0.367 [+0.239, +0.487]; vs trend: +0.022 [+0.003, +0.049]; vs level: +0.009 [+0.000, +0.018] | PASS |
| 3h | 23.4% | 0.894 | 0.620 | 0.735 | 0.871 | vs yesterday: +0.274 [+0.161, +0.375]; vs trend: +0.160 [+0.101, +0.216]; vs level: +0.023 [+0.005, +0.048] | PASS |
| 6h | 32.3% | 0.863 | 0.667 | 0.642 | 0.813 | vs yesterday: +0.197 [+0.093, +0.286]; vs trend: +0.221 [+0.153, +0.286]; vs level: +0.051 [+0.018, +0.088] | PASS |

**3 of 3 windows pass** the pre-registered rule (per window, unseen ponds: lower end of the 99% interval of (model average-precision minus each baseline average-precision) > 0 for ALL THREE baselines).

### Same models on seen ponds (context)

| window | event rate | model AP | yesterday AP | trend AP | level AP |
|---|---|---|---|---|---|
| 1h | 17.1% | 0.950 | 0.578 | 0.923 | 0.937 |
| 3h | 23.4% | 0.902 | 0.620 | 0.735 | 0.871 |
| 6h | 32.3% | 0.872 | 0.667 | 0.642 | 0.813 |

### Are the probabilities trustworthy? (unseen ponds; bins by predicted probability)

| window | Brier score | predicted 0-10% -> actual | 10-30% | 30-50% | 50-70% | 70-90% | 90-100% |
|---|---|---|---|---|---|---|---|
| 1h | 0.032 | 0% -> 2% (n=8481) | 18% -> 49% (n=198) | 40% -> 60% (n=101) | 61% -> 70% (n=98) | 81% -> 91% (n=154) | 99% -> 98% (n=1217) |
| 3h | 0.065 | 1% -> 5% (n=7629) | 17% -> 30% (n=509) | 40% -> 48% (n=193) | 60% -> 69% (n=191) | 81% -> 81% (n=251) | 99% -> 97% (n=1445) |
| 6h | 0.114 | 1% -> 9% (n=6231) | 17% -> 31% (n=921) | 39% -> 44% (n=354) | 60% -> 48% (n=347) | 81% -> 70% (n=479) | 98% -> 94% (n=1897) |

### Episode-level view, 6 h window, unseen ponds (descriptive). Alert when P(event) >= 0.3

An episode starts at the first reading below 2.0 mg/L after 6 h without one; it is 'caught' if an alert fires 1-6 h earlier. Each baseline gets the strictest alert level that still catches at least as many episodes as the model (favours the baseline).

| method | episodes | caught | recall | median warning (h) | pond-days with a false alarm | share of pond-days |
|---|---|---|---|---|---|---|
| model (P >= 0.3) | 76 | 58 | 76% | 5.25 | 75 / 125 | 60% |
| same window yesterday | 76 | 58 | 76% | 5.88 | 70 / 125 | 56% |
| trend | 76 | 58 | 76% | 5.00 | 79 / 125 | 63% |
| current level | 76 | 58 | 76% | 2.88 | 91 / 125 | 73% |

Onsets not counted because they fall outside these ponds' evaluation windows (no evaluation origin 1-6 h before them): 273. The 76 counted episodes are the ones inside the evaluation windows.