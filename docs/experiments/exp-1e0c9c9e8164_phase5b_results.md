# Phase 5b results, experiment `exp-1e0c9c9e8164`

- Split `sp-2dd59e32cff4` (unchanged), Phase 3 features `ft-30c94e8fe1bd` + daily-pattern features `daily-v1`, code commit `b22fb95-unco`
- One anchored-residual LightGBM, fixed Phase 5 settings, no tuning, one round. Seeds [0, 1, 2]. Intervals are **99%** blocked-bootstrap (blocks = pond x day).
- Compute: 580.2 container-seconds, 2 CPU cores each, no GPU. **Validation-side only; sealed test not used.**
- Pre-registered success rule: per (target, horizon) on unseen ponds: lower end of the 99% interval of improvement over BOTH 'same as now' and 'same time yesterday' is > 0.
- Recommendation rule: use quality-blind if it passes; use quality-aware only if it passes AND is clearly better than blind (99% interval of aware-minus-blind MAE < 0); else best simple guess.

## 1. Average miss (MAE, native units) with intervals

### DO (mg/L)

| model | seen 15 min | seen 1 h | seen 6 h | unseen 15 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.509 [0.457, 0.561] | 1.209 [1.114, 1.306] | 4.792 [4.441, 5.168] | 0.509 [0.457, 0.564] | 1.209 [1.111, 1.315] | 4.792 [4.459, 5.151] |
| seasonal_naive | 2.082 [1.833, 2.312] | 2.083 [1.833, 2.324] | 2.060 [1.793, 2.341] | 2.082 [1.844, 2.325] | 2.083 [1.851, 2.328] | 2.060 [1.815, 2.363] |
| anch_blind | 0.461 [0.411, 0.510] | 0.850 [0.775, 0.924] | 1.688 [1.514, 1.867] | 0.479 [0.431, 0.527] | 0.910 [0.831, 0.984] | 1.807 [1.638, 1.987] |
| anch_aware | 0.439 [0.398, 0.482] | 0.845 [0.778, 0.925] | 1.689 [1.509, 1.866] | 0.454 [0.410, 0.502] | 0.897 [0.827, 0.971] | 1.836 [1.675, 2.010] |

### pH (pH units)

| model | seen 15 min | seen 1 h | seen 6 h | unseen 15 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.035 [0.019, 0.056] | 0.050 [0.035, 0.068] | 0.134 [0.117, 0.153] | 0.035 [0.020, 0.057] | 0.050 [0.037, 0.068] | 0.134 [0.117, 0.153] |
| seasonal_naive | 0.078 [0.062, 0.096] | 0.077 [0.061, 0.097] | 0.077 [0.060, 0.096] | 0.078 [0.061, 0.095] | 0.077 [0.061, 0.096] | 0.077 [0.060, 0.096] |
| anch_blind | 0.033 [0.021, 0.048] | 0.043 [0.031, 0.059] | 0.071 [0.059, 0.086] | 0.040 [0.024, 0.060] | 0.049 [0.034, 0.066] | 0.084 [0.069, 0.101] |
| anch_aware | 0.033 [0.021, 0.048] | 0.043 [0.032, 0.058] | 0.070 [0.058, 0.084] | 0.041 [0.025, 0.060] | 0.049 [0.034, 0.066] | 0.085 [0.070, 0.102] |

### Temp (°C)

| model | seen 15 min | seen 1 h | seen 6 h | unseen 15 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|
| persistence | 0.127 [0.081, 0.185] | 0.240 [0.197, 0.293] | 0.834 [0.762, 0.902] | 0.127 [0.080, 0.190] | 0.240 [0.196, 0.293] | 0.834 [0.761, 0.905] |
| seasonal_naive | 0.498 [0.428, 0.566] | 0.496 [0.420, 0.568] | 0.487 [0.405, 0.570] | 0.498 [0.428, 0.578] | 0.496 [0.427, 0.566] | 0.487 [0.406, 0.566] |
| anch_blind | 0.129 [0.086, 0.180] | 0.177 [0.139, 0.221] | 0.410 [0.363, 0.456] | 0.141 [0.094, 0.196] | 0.190 [0.145, 0.239] | 0.408 [0.363, 0.461] |
| anch_aware | 0.128 [0.090, 0.179] | 0.177 [0.135, 0.223] | 0.406 [0.364, 0.455] | 0.140 [0.093, 0.197] | 0.191 [0.148, 0.244] | 0.412 [0.366, 0.465] |

## 2. Success rule on unseen ponds (improvement over each simple guess; lower end of interval must be > 0 for BOTH)

| target | ahead | version | vs 'same as now' | vs 'same time yesterday' | verdict |
|---|---|---|---|---|---|
| DO | 15 min | anch_blind | +5.8% [+2.5, +8.8] | +76.9% [+73.8, +79.7] | PASS |
| DO | 15 min | anch_aware | +10.8% [+7.8, +13.4] | +78.1% [+75.3, +80.5] | PASS |
| DO | 1 h | anch_blind | +24.8% [+20.7, +28.5] | +56.3% [+51.5, +60.4] | PASS |
| DO | 1 h | anch_aware | +25.9% [+21.9, +29.3] | +56.9% [+51.8, +61.0] | PASS |
| DO | 6 h | anch_blind | +62.3% [+58.1, +66.0] | +12.6% [+3.6, +20.8] | PASS |
| DO | 6 h | anch_aware | +61.7% [+57.8, +65.3] | +11.3% [+1.5, +19.4] | PASS |
| pH | 15 min | anch_blind | -12.7% [-26.2, -6.5] | +48.4% [+35.1, +63.6] | fail |
| pH | 15 min | anch_aware | -14.6% [-29.4, -7.8] | +47.5% [+33.9, +63.1] | fail |
| pH | 1 h | anch_blind | +3.8% [-0.6, +7.3] | +36.9% [+27.6, +47.2] | fail |
| pH | 1 h | anch_aware | +3.2% [-1.2, +7.1] | +36.5% [+27.1, +46.6] | fail |
| pH | 6 h | anch_blind | +37.2% [+28.4, +45.2] | -9.4% [-27.1, +3.0] | fail |
| pH | 6 h | anch_aware | +36.8% [+27.4, +44.8] | -10.2% [-28.6, +4.5] | fail |
| Temp | 15 min | anch_blind | -11.4% [-23.1, -5.5] | +71.5% [+62.4, +80.1] | fail |
| Temp | 15 min | anch_aware | -10.2% [-20.1, -4.7] | +71.8% [+61.6, +80.2] | fail |
| Temp | 1 h | anch_blind | +20.9% [+16.0, +26.3] | +61.7% [+52.7, +69.9] | PASS |
| Temp | 1 h | anch_aware | +20.1% [+15.3, +26.0] | +61.4% [+52.4, +68.8] | PASS |
| Temp | 6 h | anch_blind | +51.1% [+45.4, +56.6] | +15.9% [+5.3, +24.7] | PASS |
| Temp | 6 h | anch_aware | +50.6% [+45.0, +55.8] | +15.1% [+4.9, +23.0] | PASS |

## 3. Does quality information help? (aware minus blind MAE, unseen; negative = aware better)

| target | 15 min | 1 h | 6 h |
|---|---|---|---|
| DO | -0.0252 [-0.0359, -0.0139] | -0.0133 [-0.0209, -0.0055] | 0.0288 [0.0090, 0.0487] |
| pH | 0.0007 [0.0001, 0.0013] | 0.0003 [-0.0002, 0.0008] | 0.0006 [-0.0005, 0.0017] |
| Temp | -0.0015 [-0.0031, -0.0001] | 0.0017 [0.0003, 0.0032] | 0.0041 [-0.0019, 0.0097] |

## 4. What each cell should use (applying the recommendation rule mechanically)

| target | ahead | use | simple-guess MAEs (now / yesterday) | chosen MAE |
|---|---|---|---|---|
| DO | 15 min | anchored LightGBM, quality-blind | 0.509 / 2.082 | 0.479 |
| DO | 1 h | anchored LightGBM, quality-blind | 1.209 / 2.083 | 0.910 |
| DO | 6 h | anchored LightGBM, quality-blind | 4.792 / 2.060 | 1.807 |
| pH | 15 min | 'same as now' | 0.035 / 0.078 | 0.035 |
| pH | 1 h | 'same as now' | 0.050 / 0.077 | 0.050 |
| pH | 6 h | 'same time yesterday' | 0.134 / 0.077 | 0.077 |
| Temp | 15 min | 'same as now' | 0.127 / 0.498 | 0.127 |
| Temp | 1 h | anchored LightGBM, quality-blind | 0.240 / 0.496 | 0.190 |
| Temp | 6 h | anchored LightGBM, quality-blind | 0.834 / 0.487 | 0.408 |

## 5. Against the Phase 5 LightGBM (level model), same rows; positive = anchored is better

| target | version | seen 15 min | seen 1 h | seen 6 h | unseen 15 min | unseen 1 h | unseen 6 h |
|---|---|---|---|---|---|---|---|
| DO | anch_blind | +0.3% [-1.2, +1.9] | +1.2% [-0.9, +3.2] | +8.9% [+2.3, +15.2] | +1.2% [-0.9, +3.4] | +2.9% [-0.1, +5.3] | +14.4% [+8.5, +20.0] |
| DO | anch_aware | +1.9% [+0.4, +3.6] | +1.4% [-0.8, +3.2] | +8.4% [+1.9, +14.8] | +2.8% [+1.2, +4.4] | +4.2% [+1.6, +6.7] | +13.2% [+6.8, +19.1] |
| pH | anch_blind | +8.1% [+4.2, +14.1] | +1.3% [-1.4, +3.4] | +7.3% [+0.6, +14.5] | +8.2% [+3.2, +15.5] | +1.7% [-1.4, +4.9] | +12.9% [+5.2, +20.4] |
| pH | anch_aware | +7.8% [+4.0, +14.6] | +1.7% [-1.1, +3.8] | +8.3% [+1.9, +14.3] | +2.8% [-1.9, +9.7] | +1.8% [-1.2, +5.2] | +12.7% [+5.4, +20.2] |
| Temp | anch_blind | +13.5% [+4.3, +24.8] | +13.8% [+6.0, +22.8] | -0.1% [-7.7, +6.5] | +16.8% [+5.9, +31.2] | +16.5% [+7.6, +27.1] | +6.3% [-1.4, +12.8] |
| Temp | anch_aware | +13.7% [+4.7, +26.0] | +14.5% [+6.9, +24.2] | +2.1% [-5.4, +8.8] | +17.6% [+7.0, +30.8] | +14.7% [+5.7, +24.9] | +6.0% [-1.1, +13.0] |

## 6. Hard cases: bottom 10% of training values, unseen ponds (MAE, with n)

| target | model | 15 min | 1 h | 6 h |
|---|---|---|---|---|
| DO | persistence | 0.223 [0.161, 0.315] (n=1142) | 0.478 [0.382, 0.591] (n=1146) | 2.840 [2.379, 3.360] (n=1146) |
| DO | seasonal_naive | 1.234 [0.863, 1.623] (n=1142) | 1.236 [0.887, 1.650] (n=1146) | 1.232 [0.902, 1.629] (n=1146) |
| DO | anch_blind | 0.252 [0.185, 0.335] (n=1142) | 0.491 [0.380, 0.613] (n=1146) | 1.432 [1.151, 1.710] (n=1146) |
| DO | anch_aware | 0.224 [0.168, 0.302] (n=1142) | 0.476 [0.372, 0.595] (n=1146) | 1.523 [1.235, 1.804] (n=1146) |
| pH | persistence | 0.032 [0.018, 0.066] (n=1130) | 0.046 [0.032, 0.076] (n=1128) | 0.110 [0.092, 0.146] (n=1128) |
| pH | seasonal_naive | 0.073 [0.053, 0.108] (n=1130) | 0.073 [0.055, 0.109] (n=1128) | 0.072 [0.053, 0.107] (n=1128) |
| pH | anch_blind | 0.043 [0.027, 0.080] (n=1130) | 0.055 [0.040, 0.089] (n=1128) | 0.143 [0.104, 0.200] (n=1128) |
| pH | anch_aware | 0.048 [0.030, 0.089] (n=1130) | 0.058 [0.043, 0.094] (n=1128) | 0.144 [0.105, 0.199] (n=1128) |
| Temp | persistence | 0.080 [0.036, 0.146] (n=3505) | 0.138 [0.095, 0.197] (n=3436) | 0.420 [0.378, 0.467] (n=3184) |
| Temp | seasonal_naive | 0.382 [0.300, 0.483] (n=3505) | 0.379 [0.303, 0.474] (n=3436) | 0.366 [0.285, 0.470] (n=3184) |
| Temp | anch_blind | 0.093 [0.051, 0.155] (n=3505) | 0.138 [0.091, 0.215] (n=3436) | 0.384 [0.338, 0.439] (n=3184) |
| Temp | anch_aware | 0.091 [0.046, 0.158] (n=3505) | 0.141 [0.094, 0.210] (n=3436) | 0.385 [0.328, 0.441] (n=3184) |

## 7. How often 'yesterday' was missing at 6 h (anchor fell back to 'same as now')

| target | evaluation rows | training rows |
|---|---|---|
| DO | 3.1% | 6.9% |
| Temp | 3.1% | 6.9% |
| pH | 3.1% | 6.9% |

## 8. Seed stability: largest (max-min)/mean MAE across seeds **19.99%** (median 1.97%)