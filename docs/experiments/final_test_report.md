# Phase 11 results: the sealed final test (run once)

- Contract `configs/final_test.yaml`, committed before any sealed row was read. Bundle `final_v1` (manifest sha256 `fe4e68a0ef0b0c5e...`), code commit `924f35e375dd`.
- Run started 2026-11-14 09:09:23 UTC, completed 2026-11-14 09:09:32 UTC. **One run.** Intervals: 99% blocked bootstrap (blocks = pond x calendar day).
- Sealed (never-seen) ponds: ara2_3ed4df8e, ara2_45e1cde5, ara2_b3d128ac, ara2_d52ddb31; 3,900 test-window origins. Development ponds, test window: 10,611 origins.
- Models were trained on development ponds, training + validation windows only. Nothing was refit, tuned or selected on the test.

## A. Forecast accuracy on the sealed ponds (average miss, MAE)

| target | ahead | method used by the app | app (99% interval) | 'same as now' | 'same time yesterday' | validation MAE of the app method | vs 'same as now' | vs 'same time yesterday' | verdict |
|---|---|---|---|---|---|---|---|---|---|
| Oxygen (mg/L) | 15 min | trained model | 0.329 [0.293, 0.365] | 0.387 [0.352, 0.428] | 1.548 [1.294, 1.846] | 0.479 | +14.8% [+10.7, +18.7] | +78.7% [+73.8, +82.9] | **PASS** |
| Oxygen (mg/L) | 1 h | trained model | 0.714 [0.628, 0.802] | 1.115 [1.017, 1.208] | 1.541 [1.287, 1.832] | 0.910 | +36.0% [+27.7, +42.5] | +54.0% [+43.9, +62.7] | **PASS** |
| Oxygen (mg/L) | 6 h | trained model | 1.655 [1.412, 1.930] | 4.889 [4.379, 5.346] | 1.520 [1.265, 1.836] | 1.807 | +66.2% [+61.0, +71.8] | -5.6% [-25.3, +11.0] | **fail** |
| pH (pH units) | 15 min | same as now | 0.009 [0.007, 0.013] | 0.009 [0.007, 0.013] | 0.036 [0.027, 0.047] | 0.035 | +0.0% [+0.0, +0.0] | +74.3% [+63.7, +80.6] | no claim (plain guess) |
| pH (pH units) | 1 h | same as now | 0.022 [0.018, 0.026] | 0.022 [0.018, 0.026] | 0.036 [0.027, 0.045] | 0.050 | +0.0% [+0.0, +0.0] | +39.4% [+23.7, +50.6] | no claim (plain guess) |
| pH (pH units) | 6 h | same time yesterday | 0.038 [0.029, 0.049] | 0.090 [0.072, 0.108] | 0.035 [0.027, 0.046] | 0.077 | +57.9% [+48.3, +65.9] | +0.0% [+0.0, +0.0] | no claim (plain guess) |
| Temperature (°C) | 15 min | same as now | 0.045 [0.040, 0.051] | 0.045 [0.040, 0.051] | 0.208 [0.173, 0.252] | 0.127 | +0.0% [+0.0, +0.0] | +78.5% [+72.7, +82.8] | no claim (plain guess) |
| Temperature (°C) | 1 h | trained model | 0.098 [0.087, 0.113] | 0.143 [0.126, 0.159] | 0.206 [0.170, 0.246] | 0.190 | +31.5% [+20.9, +39.9] | +52.7% [+41.2, +61.7] | **PASS** |
| Temperature (°C) | 6 h | trained model | 0.250 [0.213, 0.291] | 0.667 [0.591, 0.741] | 0.203 [0.156, 0.246] | 0.408 | +62.5% [+56.2, +67.8] | -20.3% [-50.4, -0.2] | **fail** |

**3 of 5 model cells pass** (rule F1: lower end of the 99% interval above 0 against both plain guesses). Forecasting is therefore **not** called validated; see the failed cells above.

### Context: development ponds, test window (ponds the models saw, later days)

| target | ahead | app | 'same as now' | 'same time yesterday' |
|---|---|---|---|---|
| Oxygen | 15 min | 0.408 [0.369, 0.449] | 0.482 [0.438, 0.531] | 1.504 [1.354, 1.655] |
| Oxygen | 1 h | 0.757 [0.697, 0.822] | 1.217 [1.142, 1.292] | 1.499 [1.349, 1.645] |
| Oxygen | 6 h | 1.428 [1.270, 1.610] | 4.945 [4.704, 5.196] | 1.483 [1.336, 1.637] |
| pH | 15 min | 0.012 [0.010, 0.013] | 0.012 [0.010, 0.013] | 0.040 [0.035, 0.045] |
| pH | 1 h | 0.030 [0.026, 0.034] | 0.030 [0.027, 0.033] | 0.040 [0.035, 0.045] |
| pH | 6 h | 0.042 [0.037, 0.048] | 0.125 [0.111, 0.141] | 0.039 [0.034, 0.045] |
| Temperature | 15 min | 0.053 [0.049, 0.058] | 0.053 [0.049, 0.058] | 0.229 [0.208, 0.252] |
| Temperature | 1 h | 0.096 [0.089, 0.103] | 0.170 [0.159, 0.181] | 0.229 [0.207, 0.253] |
| Temperature | 6 h | 0.230 [0.204, 0.258] | 0.782 [0.729, 0.833] | 0.227 [0.200, 0.256] |

## B. Do the 'likely between' ranges hold? (target 90%, sealed ponds)

| target | ahead | coverage (99% interval) | day / night / low-value coverage | rows in the low-value group | per-pond coverage (min-max) | verdict |
|---|---|---|---|---|---|---|
| Oxygen | 15 min | 94.9% [93.4, 96.2] | 91% / 99% / 99% | 381 | 94%-97% | fail |
| Oxygen | 1 h | 94.4% [91.7, 96.6] | 93% / 96% / 99% | 381 | 89%-97% | fail |
| Oxygen | 6 h | 91.8% [87.1, 95.6] | 92% / 91% / 99% | 358 | 79%-98% | PASS |
| pH | 15 min | 99.2% [98.6, 99.6] | 99% / 100% / 0% | 1 | 98%-100% | fail |
| pH | 1 h | 98.9% [98.0, 99.5] | 98% / 100% / 0% | 1 | 96%-100% | fail |
| pH | 6 h | 97.3% [93.2, 99.5] | 97% / 98% / 0% | 1 | 92%-100% | fail |
| Temperature | 15 min | 98.7% [98.0, 99.3] | 98% / 100% / nan% | 0 | 98%-99% | fail |
| Temperature | 1 h | 98.5% [97.2, 99.4] | 99% / 98% / nan% | 0 | 98%-99% | fail |
| Temperature | 6 h | 97.3% [94.8, 99.3] | 99% / 96% / nan% | 0 | 91%-100% | fail |

**1 of 9 range cells pass** (rule R1).

## C. Low-oxygen chance (below 2 mg/L), sealed ponds

| window | event rate | model AP | yesterday AP | trend AP | level AP | model minus each baseline (99% interval) | verdict |
|---|---|---|---|---|---|---|---|
| next hour | 16.8% | 0.968 | 0.568 | 0.955 | 0.953 | vs yesterday: +0.400 [+0.140, +0.584]; vs trend: +0.013 [-0.001, +0.035]; vs level: +0.015 [+0.009, +0.028] | fail |
| next 3 hours | 23.2% | 0.930 | 0.616 | 0.723 | 0.896 | vs yesterday: +0.314 [+0.106, +0.468]; vs trend: +0.207 [+0.126, +0.312]; vs level: +0.035 [+0.012, +0.068] | PASS |
| next 6 hours | 32.7% | 0.886 | 0.661 | 0.612 | 0.831 | vs yesterday: +0.225 [+0.057, +0.334]; vs trend: +0.274 [+0.161, +0.369]; vs level: +0.055 [+0.009, +0.108] | PASS |

**2 of 3 windows pass** (rule A1).

### Calibration of the app's percentages (rule A2)

| window | Brier raw | Brier calibrated | bins (calibrated -> actual, n) | criterion |
|---|---|---|---|---|
| next hour | 0.0200 | 0.0235 | 2% -> 1% (3016); 18% -> 8% (114); 48% -> 22% (46); 59% -> 40% (110); 88% -> 81% (130); 99% -> 99% (468) | fail |
| next 3 hours | 0.0491 | 0.0525 | 6% -> 2% (2311); 17% -> 7% (511); 41% -> 33% (161); 61% -> 58% (97); 81% -> 71% (245); 99% -> 98% (545) | fail |
| next 6 hours | 0.0950 | 0.1010 | 9% -> 7% (630); 18% -> 4% (1498); 42% -> 35% (651); 64% -> 65% (204); 84% -> 83% (382); 100% -> 98% (475) | fail |

**0 of 3 windows pass** the calibration criterion.

### Episodes, 6 h window (descriptive, rule A3): the app says 'High chance' at a calibrated 31% or more

| method | episodes | caught | recall | median warning (h) | pond-days with a false alarm | share |
|---|---|---|---|---|---|---|
| app | 31 | 29 | 94% | 6.00 | 43 / 44 | 98% |
| same window yesterday (strictest level matching the app's recall; favours it) | 31 | 29 | 94% | 6.00 | 33 / 44 | 75% |

## Summary against the pre-registered rules

| rule | result |
|---|---|
| F1 model cells beating both plain guesses (99%) | 3 of 5 |
| R1 range cells with valid coverage | 1 of 9 |
| A1 alert beats all three baselines | 2 of 3 windows |
| A2 alert percentages calibrated | 0 of 3 windows |