# Phase 1b-R results: method replication on BCO-DMO 988873 (salt-marsh ponds), experiment `exp-20f6d2ca9f07`

- Contract `configs/replication_bco.yaml` (frozen before any code ran). Split `bsp-50f01c356bb7`, features `bco-10b684a9730d`, code commit `355856a-unco`.
- Validation-side only. Held-out ponds: Drum, Long Reach, Ring East, White (one pond per fold). **The sealed pond (Shark) and the test window were not used.**
- Dataset limits: tidal salt marsh, not managed aquaculture; 30-minute subsample of a 10-minute series; oxygen converted from umol/kg (approximate density). Intervals are 99% blocked bootstrap (blocks = pond x day).

## 0. Data facts that shape every result below (per pond, valid readings on the 30-minute grid)

| pond | oxygen valid | pH valid | temperature valid | oxygen <= 0.05 mg/L (share of valid) | oxygen < 2 mg/L (share of valid) |
|---|---|---|---|---|---|
| Drum | 97.6% | 98.3% | 98.3% | 11.64% | 20.0% |
| Long Reach | 98.3% | 98.3% | 98.3% | 15.37% | 25.7% |
| Ring East | 98.1% | 98.1% | 98.7% | 17.57% | 27.3% |
| Shark | 98.2% | 98.2% | 98.3% | 13.72% | 24.6% |
| White | 86.8% | 73.0% | 86.8% | 18.07% | 28.5% |

Near-zero oxygen is common (about 12% to 18% of valid readings). Per the contract these values are kept as valid and no run with them masked was made.

## A. Forecast accuracy: average miss (MAE) with 99% intervals

### DO (mg/L)

| model | seen 30 min | seen 1 h | seen 6 h | unseen 30 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.321 [0.289, 0.353] | 0.489 [0.445, 0.535] | 1.534 [1.394, 1.684] | 0.321 [0.290, 0.352] | 0.489 [0.445, 0.537] | 1.534 [1.389, 1.674] |
| seasonal_naive | 1.038 [0.954, 1.124] | 1.038 [0.950, 1.133] | 1.038 [0.950, 1.135] | 1.038 [0.951, 1.132] | 1.038 [0.949, 1.136] | 1.038 [0.946, 1.126] |
| anch_blind | 0.336 [0.307, 0.367] | 0.490 [0.453, 0.530] | 1.042 [0.965, 1.122] | 0.344 [0.312, 0.375] | 0.515 [0.477, 0.556] | 1.097 [1.017, 1.181] |

### pH (pH units)

| model | seen 30 min | seen 1 h | seen 6 h | unseen 30 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.064 [0.059, 0.069] | 0.096 [0.089, 0.104] | 0.294 [0.270, 0.318] | 0.064 [0.058, 0.069] | 0.096 [0.089, 0.104] | 0.294 [0.272, 0.318] |
| seasonal_naive | 0.210 [0.189, 0.235] | 0.210 [0.188, 0.232] | 0.210 [0.187, 0.233] | 0.210 [0.188, 0.233] | 0.210 [0.187, 0.235] | 0.210 [0.189, 0.232] |
| anch_blind | 0.068 [0.062, 0.073] | 0.095 [0.088, 0.103] | 0.174 [0.161, 0.187] | 0.070 [0.064, 0.076] | 0.102 [0.094, 0.110] | 0.201 [0.186, 0.217] |

### Temp (°C)

| model | seen 30 min | seen 1 h | seen 6 h | unseen 30 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.157 [0.147, 0.168] | 0.305 [0.283, 0.327] | 1.469 [1.364, 1.580] | 0.157 [0.146, 0.168] | 0.305 [0.283, 0.326] | 1.469 [1.358, 1.577] |
| seasonal_naive | 1.557 [1.406, 1.708] | 1.558 [1.413, 1.707] | 1.569 [1.427, 1.715] | 1.557 [1.417, 1.708] | 1.558 [1.413, 1.701] | 1.569 [1.431, 1.711] |
| anch_blind | 0.074 [0.069, 0.079] | 0.141 [0.132, 0.151] | 0.857 [0.801, 0.917] | 0.075 [0.070, 0.081] | 0.143 [0.134, 0.154] | 0.881 [0.829, 0.935] |

### Pre-registered success rule per cell (held-out ponds): improvement over BOTH simple guesses, lower end of the 99% interval must be > 0

| target | ahead | vs 'same as now' | vs 'same time yesterday' | verdict |
|---|---|---|---|---|
| DO | 30 min | -7.3% [-11.0, -4.1] | +66.6% [+63.3, +69.5] | fail |
| DO | 1 h | -5.3% [-10.4, -0.7] | +50.2% [+46.0, +53.9] | fail |
| DO | 6 h | +28.4% [+22.3, +33.8] | -5.6% [-13.0, +0.8] | fail |
| pH | 30 min | -9.5% [-13.2, -6.5] | +66.4% [+62.8, +69.5] | fail |
| pH | 1 h | -5.4% [-9.4, -1.5] | +51.0% [+46.0, +55.6] | fail |
| pH | 6 h | +31.8% [+27.2, +35.6] | +3.9% [-5.6, +11.6] | fail |
| Temp | 30 min | +52.1% [+48.9, +55.2] | +95.2% [+94.6, +95.7] | PASS |
| Temp | 1 h | +52.9% [+49.6, +56.0] | +90.8% [+89.7, +91.7] | PASS |
| Temp | 6 h | +40.1% [+35.6, +44.3] | +44.0% [+39.2, +48.5] | PASS |

**3 of 9 cells pass.** A 6 h cell passes: True. **Pre-registered verdict on 'the method replicates': YES** (needs at least 3 of 9 cells and at least one 6 h cell).

## B. Forecast ranges (split-conformal, 90% target), held-out ponds

Centre of each range = the model if its cell passed, otherwise the better simple guess (same mechanical rule as Phase 5b). Calibration = the other three held-out ponds.

| target | ahead | centre | coverage (plain) | half-width | day / night / low-value coverage | coverage (day/night variant) | day / night / low | per-pond coverage (min-max) | verdict |
|---|---|---|---|---|---|---|---|---|---|
| DO (mg/L) | 30 min | persistence | 90.0% [88.2, 91.5] | ±0.758 | 84% / 96% / 94% | 89.5% | 89% / 90% / 97% | 76%-96% | PASS (day/night) |
| DO (mg/L) | 1 h | persistence | 89.9% [88.2, 91.6] | ±1.147 | 83% / 96% / 79% | 89.7% | 89% / 90% / 88% | 76%-96% | PASS (day/night) |
| DO (mg/L) | 6 h | seasonal_naive | 90.2% [88.3, 92.2] | ±2.347 | 91% / 90% / 62% | 90.1% | 90% / 90% / 62% | 76%-94% | fail |
| pH (pH units) | 30 min | persistence | 90.0% [88.5, 91.6] | ±0.157 | 84% / 96% / 90% | 89.8% | 89% / 90% / 92% | 84%-95% | PASS (day/night) |
| pH (pH units) | 1 h | persistence | 89.9% [88.5, 91.3] | ±0.242 | 83% / 97% / 88% | 89.9% | 90% / 90% / 90% | 84%-94% | PASS (day/night) |
| pH (pH units) | 6 h | seasonal_naive | 90.3% [87.8, 92.6] | ±0.547 | 89% / 91% / 74% | 90.3% | 90% / 90% / 73% | 83%-94% | fail |
| Temp (°C) | 30 min | anch_blind | 90.0% [88.5, 91.3] | ±0.162 | 87% / 93% / 91% | 89.9% | 90% / 90% / 91% | 90%-91% | PASS (plain) |
| Temp (°C) | 1 h | anch_blind | 89.9% [88.2, 91.4] | ±0.321 | 86% / 94% / 91% | 90.0% | 90% / 90% / 91% | 87%-92% | PASS (plain) |
| Temp (°C) | 6 h | anch_blind | 90.0% [88.0, 91.9] | ±1.914 | 85% / 95% / 91% | 90.1% | 90% / 90% / 91% | 87%-92% | PASS (day/night) |

**7 of 9 cells pass** the pre-registered coverage rule.

## C. Low-oxygen early warning (any reading below 2.0 mg/L within the next window), held-out ponds

| window | event rate | model AP | yesterday AP | trend AP | level AP | model minus each baseline (99% interval) | verdict |
|---|---|---|---|---|---|---|---|
| 1 h | 2.1% | 0.791 | 0.488 | 0.767 | 0.778 | vs yesterday: +0.303 [+0.156, +0.440]; vs trend: +0.024 [-0.039, +0.074]; vs level: +0.014 [-0.039, +0.049] | fail |
| 3 h | 3.3% | 0.682 | 0.536 | 0.588 | 0.645 | vs yesterday: +0.146 [+0.035, +0.266]; vs trend: +0.094 [-0.001, +0.173]; vs level: +0.037 [-0.056, +0.108] | fail |
| 6 h | 5.0% | 0.610 | 0.577 | 0.446 | 0.516 | vs yesterday: +0.033 [-0.077, +0.140]; vs trend: +0.164 [+0.037, +0.274]; vs level: +0.094 [-0.027, +0.194] | fail |

**0 of 3 windows pass** the pre-registered rule (all three baselines, 99%).

### Calibration (isotonic fitted on the other three ponds)

| window | Brier raw | Brier calibrated | bins (calibrated -> actual, n) | criterion |
|---|---|---|---|---|
| 1 h | 0.0083 | 0.0085 | 0% -> 0% (12271); 21% -> 19% (173); 42% -> 38% (73); 67% -> 75% (12); 85% -> 86% (112); 96% -> 90% (62) | fail |
| 3 h | 0.0181 | 0.0180 | 1% -> 1% (11915); 16% -> 9% (371); 39% -> 56% (143); 56% -> 42% (69); 78% -> 45% (44); 95% -> 94% (147) | fail |
| 6 h | 0.0341 | 0.0319 | 1% -> 2% (11428); 18% -> 23% (735); 39% -> 33% (243); 56% -> 31% (61); 85% -> 54% (35); 96% -> 95% (166) | PASS |

**1 of 3 windows pass** the calibration criterion.

### Decision rule (6 h): alert level chosen on the other ponds for >= 80% episode recall, then applied to the held-out pond

| held-out pond fold | model recall | model false-alarm days | baseline ('same window yesterday') recall | baseline false-alarm days |
|---|---|---|---|---|
| fold0 | 2/2 | 34/82 | 0/2 | 20/82 |
| fold1 | 16/17 | 52/81 | 15/17 | 55/81 |
| fold2 | 1/4 | 17/81 | 1/4 | 23/81 |
| fold3 | 11/13 | 23/33 | 13/13 | 31/33 |

Pooled: model catches 30/36 episodes (83%), median warning 6.00 h, false-alarm share 45% of pond-days. Baseline catches 29/36 (81%), median warning 6.00 h, false-alarm share 47%.
False-alarm share, model minus baseline: **-1.1 points** (99% interval -10.1 to +7.6, n=277 pond-days). **Pre-registered verdict: FAIL.**

## Summary against the pre-registered rules

| rule | result |
|---|---|
| Forecast cells beating both simple guesses (99%) | 3 of 9; method replicates: **YES** |
| Range coverage rule | 7 of 9 cells pass |
| Alert beats 3 baselines (AP, 99%) | 0 of 3 windows |
| Alert calibration criterion | 1 of 3 windows |
| Alert false-alarm decision rule | FAIL |