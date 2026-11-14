# Phases 7 and 8 results: SHAP explanations and explanation validation, experiment `exp-570e678b7197`

- Contract `configs/explain.yaml` (written before any SHAP value existed). Code commit `1734bb4-unco`. Validation-side only; sealed ponds and test windows not used.
- The explained models are the same anchored LightGBM models (quality-blind, fixed settings, seeds 0 to 2) evaluated in earlier phases. TreeSHAP is exact for tree models.
- **How to read this:** SHAP says how much each input pushed a prediction up or down compared with the model's average output. For forecasts, SHAP explains the model's **correction** to its starting guess (same as now, or same time yesterday). It describes what the **model** uses, not proof of what causes oxygen to fall.

## Phase 8: are the explanations trustworthy? (pre-registered tests E1 to E4)

| cell | E1 same across seeds (min rank correlation, need 0.90) | E2 same across pond groups (mean rank corr need 0.70; shared top-5 need 3) | E3 same across time (need 0.70) | E4 removing top-5 hurts more than removing 5 random (main; ponds passing of 4, need main and 3) | validated |
|---|---|---|---|---|---|
| Eluru farm ponds: low-oxygen alert, next 3 h | 0.93 PASS | 0.78 / 4.0 PASS | 0.87 PASS | extra error +0.334 [+0.245, +0.435]; 4/4 PASS | **YES** |
| Eluru farm ponds: low-oxygen alert, next 6 h | 0.94 PASS | 0.83 / 4.2 PASS | 0.93 PASS | extra error +0.176 [+0.093, +0.262]; 3/4 PASS | **YES** |
| Eluru farm ponds: low-oxygen alert, next 1 h | 0.91 PASS | 0.73 / 4.2 PASS | 0.86 PASS | extra error +0.446 [+0.323, +0.565]; 4/4 PASS | **YES** |
| Eluru farm ponds: DO 15 min ahead | 0.94 PASS | 0.76 / 4.0 PASS | 0.86 PASS | extra error +0.038 [+0.026, +0.050]; 2/4 fail | **NO** |
| Eluru farm ponds: DO 6 h ahead | 0.95 PASS | 0.84 / 4.0 PASS | 0.93 PASS | extra error +0.463 [+0.318, +0.617]; 3/4 PASS | **YES** |
| Eluru farm ponds: DO 1 h ahead | 0.94 PASS | 0.74 / 3.2 PASS | 0.90 PASS | extra error +0.413 [+0.370, +0.456]; 4/4 PASS | **YES** |
| Eluru farm ponds: Temp 6 h ahead | 0.94 PASS | 0.72 / 4.5 PASS | 0.87 PASS | extra error +0.234 [+0.171, +0.303]; 3/4 PASS | **YES** |
| Eluru farm ponds: Temp 1 h ahead | 0.95 PASS | 0.72 / 3.0 PASS | 0.87 PASS | extra error +0.137 [+0.127, +0.150]; 4/4 PASS | **YES** |
| salt-marsh ponds: Temp 30 min ahead | 0.84 fail | 0.75 / 4.2 PASS | 0.99 PASS | extra error +0.088 [+0.083, +0.093]; 4/4 PASS | **NO** |
| salt-marsh ponds: Temp 6 h ahead | 0.93 PASS | 0.81 / 5.0 PASS | 0.99 PASS | extra error +0.923 [+0.767, +1.068]; 4/4 PASS | **YES** |
| salt-marsh ponds: Temp 1 h ahead | 0.91 PASS | 0.84 / 5.0 PASS | 0.98 PASS | extra error +0.181 [+0.172, +0.190]; 4/4 PASS | **YES** |

**9 of 11 explanations are validated** (all of E1 to E4 must pass). E4 extra error is in the loss unit of the cell (forecast absolute error, or alert log-loss), 99% interval.

## Phase 7: what do the models use? (mean absolute SHAP, validation window, averaged over 3 seeds)

### Eluru farm ponds: low-oxygen alert, next 3 h (unit: log-odds)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `DO_cur` | history | 1.5053 |
| 2 | `hour_cos` | time | 0.6324 |
| 3 | `DO_dmin96` | daily | 0.5030 |
| 4 | `ydaymin_W12` | daily | 0.3906 |
| 5 | `Temp_yday_tgt_h24` | daily | 0.3205 |
| 6 | `DO_max4` | rolling | 0.2981 |
| 7 | `Temp_dmin96` | daily | 0.2587 |
| 8 | `DO_dmean96` | daily | 0.2370 |
| 9 | `DO_yday_tgt_h24` | daily | 0.2316 |
| 10 | `DO_mean4` | rolling | 0.1640 |

### Eluru farm ponds: low-oxygen alert, next 6 h (unit: log-odds)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `ydaymin_W24` | daily | 1.0008 |
| 2 | `DO_cur` | history | 0.9139 |
| 3 | `hour_cos` | time | 0.7648 |
| 4 | `DO_dmin96` | daily | 0.7126 |
| 5 | `DO_yday_tgt_h24` | daily | 0.3571 |
| 6 | `Temp_yday_tgt_h24` | daily | 0.3512 |
| 7 | `Temp_dmean96` | daily | 0.3460 |
| 8 | `DO_max4` | rolling | 0.3305 |
| 9 | `DO_dmean96` | daily | 0.3186 |
| 10 | `Temp_dmin96` | daily | 0.2437 |

### Eluru farm ponds: low-oxygen alert, next 1 h (unit: log-odds)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `DO_cur` | history | 1.6251 |
| 2 | `DO_dmin96` | daily | 0.3993 |
| 3 | `DO_mean4` | rolling | 0.3483 |
| 4 | `hour_cos` | time | 0.3129 |
| 5 | `DO_max4` | rolling | 0.2722 |
| 6 | `DO_min4` | rolling | 0.2021 |
| 7 | `DO_yday_tgt_h4` | daily | 0.1821 |
| 8 | `DO_lag1` | history | 0.1766 |
| 9 | `DO_std4` | rolling | 0.1560 |
| 10 | `Temp_slope12` | rolling | 0.1480 |

### Eluru farm ponds: DO 15 min ahead (unit: mg/L)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `DO_cur` | history | 0.2798 |
| 2 | `hour_cos` | time | 0.1943 |
| 3 | `DO_lag1` | history | 0.0935 |
| 4 | `DO_std4` | rolling | 0.0684 |
| 5 | `DO_max4` | rolling | 0.0419 |
| 6 | `DO_slope12` | rolling | 0.0417 |
| 7 | `DO_min4` | rolling | 0.0410 |
| 8 | `Temp_cur` | history | 0.0247 |
| 9 | `Temp_slope12` | rolling | 0.0240 |
| 10 | `DO_dmin96` | daily | 0.0239 |

### Eluru farm ponds: DO 6 h ahead (unit: mg/L)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `anchor_gap` | anchor_gap | 0.7950 |
| 2 | `hour_cos` | time | 0.7623 |
| 3 | `DO_yday_tgt_h24` | daily | 0.7017 |
| 4 | `hour_sin` | time | 0.4813 |
| 5 | `Temp_d1` | daily | 0.2645 |
| 6 | `DO_d1` | daily | 0.2145 |
| 7 | `DO_dmin96` | daily | 0.2043 |
| 8 | `DO_dmax96` | daily | 0.1453 |
| 9 | `Temp_dmean96` | daily | 0.1218 |
| 10 | `DO_dmean96` | daily | 0.1138 |

### Eluru farm ponds: DO 1 h ahead (unit: mg/L)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `hour_cos` | time | 0.7455 |
| 2 | `DO_cur` | history | 0.6292 |
| 3 | `DO_yday_tgt_h4` | daily | 0.1344 |
| 4 | `DO_lag1` | history | 0.1237 |
| 5 | `DO_min4` | rolling | 0.1048 |
| 6 | `DO_slope12` | rolling | 0.0888 |
| 7 | `DO_dmin96` | daily | 0.0856 |
| 8 | `Temp_slope12` | rolling | 0.0843 |
| 9 | `DO_std4` | rolling | 0.0798 |
| 10 | `DO_lag2` | history | 0.0703 |

### Eluru farm ponds: Temp 6 h ahead (unit: °C)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `anchor_gap` | anchor_gap | 0.2864 |
| 2 | `Temp_d1` | daily | 0.2130 |
| 3 | `Temp_yday_tgt_h24` | daily | 0.2127 |
| 4 | `hour_cos` | time | 0.1222 |
| 5 | `hour_sin` | time | 0.0901 |
| 6 | `Temp_cur` | history | 0.0711 |
| 7 | `Temp_dmin96` | daily | 0.0327 |
| 8 | `Temp_min24` | rolling | 0.0313 |
| 9 | `Temp_dmax96` | daily | 0.0227 |
| 10 | `Temp_dmean96` | daily | 0.0207 |

### Eluru farm ponds: Temp 1 h ahead (unit: °C)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `Temp_cur` | history | 0.1877 |
| 2 | `hour_cos` | time | 0.1150 |
| 3 | `Temp_min12` | rolling | 0.0227 |
| 4 | `Temp_std12` | rolling | 0.0214 |
| 5 | `Temp_lag2` | history | 0.0167 |
| 6 | `Temp_std4` | rolling | 0.0159 |
| 7 | `hour_sin` | time | 0.0120 |
| 8 | `DO_slope12` | rolling | 0.0120 |
| 9 | `Temp_lag4` | history | 0.0120 |
| 10 | `Temp_dmean96` | daily | 0.0116 |

### salt-marsh ponds: Temp 30 min ahead (unit: °C)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `hour_cos` | time | 0.1128 |
| 2 | `Temp_slope6` | rolling | 0.0520 |
| 3 | `hour_sin` | time | 0.0405 |
| 4 | `Temp_std2` | rolling | 0.0375 |
| 5 | `Temp_yday_tgt_h1` | daily | 0.0334 |
| 6 | `Temp_d1` | daily | 0.0247 |
| 7 | `Temp_lag1` | history | 0.0228 |
| 8 | `Temp_min6` | rolling | 0.0089 |
| 9 | `Temp_lag6` | history | 0.0081 |
| 10 | `Temp_lag2` | history | 0.0075 |

### salt-marsh ponds: Temp 6 h ahead (unit: °C)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `anchor_gap` | anchor_gap | 1.0169 |
| 2 | `Temp_d1` | daily | 0.7842 |
| 3 | `hour_sin` | time | 0.5591 |
| 4 | `hour_cos` | time | 0.2998 |
| 5 | `Temp_slope6` | rolling | 0.2985 |
| 6 | `Temp_cur` | history | 0.2370 |
| 7 | `Temp_yday_tgt_h12` | daily | 0.2134 |
| 8 | `Temp_dmax96` | daily | 0.1023 |
| 9 | `Temp_std2` | rolling | 0.0764 |
| 10 | `Temp_lag12` | history | 0.0726 |

### salt-marsh ponds: Temp 1 h ahead (unit: °C)

| rank | input | family | mean abs SHAP |
|---|---|---|---|
| 1 | `hour_cos` | time | 0.2295 |
| 2 | `hour_sin` | time | 0.0987 |
| 3 | `Temp_slope6` | rolling | 0.0868 |
| 4 | `Temp_yday_tgt_h2` | daily | 0.0801 |
| 5 | `Temp_std2` | rolling | 0.0668 |
| 6 | `Temp_lag1` | history | 0.0282 |
| 7 | `Temp_min6` | rolling | 0.0242 |
| 8 | `Temp_dmax96` | daily | 0.0180 |
| 9 | `Temp_lag6` | history | 0.0178 |
| 10 | `Temp_d1` | daily | 0.0151 |

### Share of total attribution by input family (main regime)

| cell | history | rolling | daily-pattern | time of day | anchor gap |
|---|---|---|---|---|---|
| Eluru farm ponds: low-oxygen alert, next 3 h | 27% | 28% | 37% | 8% | - |
| Eluru farm ponds: low-oxygen alert, next 6 h | 17% | 24% | 50% | 9% | - |
| Eluru farm ponds: low-oxygen alert, next 1 h | 34% | 35% | 26% | 5% | - |
| Eluru farm ponds: DO 15 min ahead | 42% | 33% | 10% | 15% | - |
| Eluru farm ponds: DO 6 h ahead | 6% | 17% | 39% | 22% | 14% |
| Eluru farm ponds: DO 1 h ahead | 32% | 29% | 14% | 25% | - |
| Eluru farm ponds: Temp 6 h ahead | 12% | 17% | 38% | 14% | 19% |
| Eluru farm ponds: Temp 1 h ahead | 41% | 31% | 10% | 18% | - |
| salt-marsh ponds: Temp 30 min ahead | 15% | 36% | 17% | 33% | - |
| salt-marsh ponds: Temp 6 h ahead | 10% | 20% | 31% | 18% | 22% |
| salt-marsh ponds: Temp 1 h ahead | 13% | 35% | 16% | 36% | - |

## Pre-registered expectations (descriptive, not gating)

**X1: At 6 h, the daily-pattern family carries at least 25% of attribution (oxygen, temperature)**

| cell | value | met |
|---|---|---|
| Eluru farm ponds: DO 6 h ahead | 39% | met |
| Eluru farm ponds: Temp 6 h ahead | 38% | met |
| salt-marsh ponds: Temp 6 h ahead | 31% | met |

**X2: At the shortest explained horizon, the history family carries at least 50%**

| cell | value | met |
|---|---|---|
| Eluru farm ponds: DO 15 min ahead | 42% | not met |
| Eluru farm ponds: Temp 1 h ahead | 41% | not met |
| salt-marsh ponds: Temp 30 min ahead | 15% | not met |

**X3: For temperature, time of day is among the top 3 families**

| cell | value | met |
|---|---|---|
| Eluru farm ponds: Temp 6 h ahead | daily, anchor_gap, rolling | not met |
| Eluru farm ponds: Temp 1 h ahead | history, rolling, time | met |
| salt-marsh ponds: Temp 30 min ahead | rolling, time, daily | met |
| salt-marsh ponds: Temp 6 h ahead | daily, anchor_gap, rolling | not met |
| salt-marsh ponds: Temp 1 h ahead | time, rolling, daily | met |

## Example explanations (anonymised, a few rows; signed SHAP)

**Eluru farm ponds: low-oxygen alert, next 3 h**
- p(event)=1.00: `DO_cur`=1.4 (+3.429); `Temp_yday_tgt_h24`=23.7 (+1.038); `hour_cos`=0.87 (+0.922); `DO_mean12`=2.09 (+0.599); `DO_max4`=1.69 (+0.569)
- p(event)=1.00: `DO_cur`=0.2 (+4.727); `DO_max4`=0.21 (+1.237); `DO_lag1`=0.2 (+0.604); `ydaymin_W12`=1.04 (+0.587); `hour_cos`=0.97 (+0.556)
- p(event)=0.98: `DO_cur`=2.49 (+2.147); `hour_cos`=0.92 (+1.701); `DO_mean4`=2.51 (+0.541); `Temp_std24`=0.09 (-0.471); `ydaymin_W12`=2.23 (+0.445)

**Eluru farm ponds: low-oxygen alert, next 6 h**
- p(event)=0.97: `hour_cos`=0.71 (+1.351); `ydaymin_W24`=1.76 (+1.238); `Temp_dmean96`=23.65 (+0.906); `Temp_yday_tgt_h24`=23.6 (+0.844); `DO_dmin96`=0.69 (+0.690)
- p(event)=0.92: `ydaymin_W24`=2.0 (+1.080); `Temp_dmean96`=24.0 (+1.073); `Temp_yday_tgt_h24`=24.1 (+0.847); `DO_dmin96`=0.28 (+0.755); `DO_yday_tgt_h24`=2.0 (+0.727)
- p(event)=0.99: `ydaymin_W24`=0.93 (+1.428); `hour_cos`=0.92 (+1.360); `Temp_dmean96`=23.74 (+1.092); `DO_yday_tgt_h24`=0.98 (+0.985); `Temp_yday_tgt_h24`=23.2 (+0.783)

**Eluru farm ponds: low-oxygen alert, next 1 h**
- p(event)=0.95: `DO_cur`=1.54 (+3.776); `DO_mean4`=1.95 (+1.101); `hour_cos`=0.83 (+0.538); `DO_dmin96`=0.47 (+0.437); `DO_max4`=2.43 (+0.418)
- p(event)=1.00: `DO_cur`=0.38 (+6.068); `DO_max4`=0.64 (+1.628); `DO_mean4`=0.52 (+1.434); `DO_dmin96`=0.38 (+0.391); `DO_min4`=0.38 (+0.319)
- p(event)=0.99: `DO_cur`=1.34 (+4.678); `DO_mean4`=1.48 (+1.182); `DO_max4`=1.6 (+0.808); `hour_cos`=0.61 (+0.444); `DO_dmin96`=0.69 (+0.337)

**Eluru farm ponds: DO 15 min ahead**
- model correction +0.047 on top of the anchor 14.10: `DO_cur`=14.1 (-0.563); `hour_cos`=-0.7 (+0.271); `DO_lag1`=13.77 (+0.241); `DO_max4`=14.1 (+0.145); `Temp_cur`=27.9 (+0.097)
- model correction -0.518 on top of the anchor 11.29: `DO_cur`=11.29 (-0.391); `hour_cos`=0.13 (-0.223); `DO_lag1`=11.65 (+0.151); `DO_max4`=12.73 (+0.114); `DO_min4`=11.29 (-0.076)

**Eluru farm ponds: DO 6 h ahead**
- model correction -0.116 on top of the anchor 10.33: `hour_sin`=-0.71 (-0.910); `hour_cos`=-0.71 (+0.627); `DO_d1`=15.3 (-0.456); `DO_std4`=1.56 (+0.287); `DO_yday_tgt_h24`=10.33 (-0.277)
- model correction +0.667 on top of the anchor 3.81: `anchor_gap`=-5.81 (+0.970); `DO_yday_tgt_h24`=3.81 (+0.680); `Temp_d1`=24.2 (+0.540); `hour_sin`=-0.97 (-0.539); `hour_cos`=0.26 (-0.525)

**Eluru farm ponds: DO 1 h ahead**
- model correction -0.585 on top of the anchor 5.25: `hour_cos`=0.9 (-0.550); `DO_dmin96`=4.29 (+0.110); `Temp_slope12`=-0.12 (-0.099); `DO_cur`=5.25 (+0.093); `Temp_lag24`=26.8 (-0.069)
- model correction +0.590 on top of the anchor 20.24: `DO_cur`=20.24 (-2.845); `hour_cos`=-0.75 (+0.984); `DO_max4`=20.24 (+0.438); `DO_lag2`=19.46 (+0.328); `DO_yday_tgt_h4`=17.55 (+0.283)

**Eluru farm ponds: Temp 6 h ahead**
- model correction +0.133 on top of the anchor 26.00: `anchor_gap`=-1.4 (+0.413); `Temp_cur`=27.4 (-0.152); `hour_sin`=-0.71 (-0.110); `Temp_d1`=27.2 (-0.074); `hour_cos`=-0.71 (+0.072)
- model correction +0.988 on top of the anchor 23.90: `Temp_d1`=24.2 (+0.620); `Temp_yday_tgt_h24`=23.9 (+0.295); `anchor_gap`=-0.5 (+0.261); `hour_sin`=-0.97 (-0.138); `hour_cos`=0.26 (-0.081)

**Eluru farm ponds: Temp 1 h ahead**
- model correction -0.068 on top of the anchor 26.00: `hour_cos`=0.9 (-0.087); `Temp_std4`=0.04 (-0.030); `Temp_dmax96`=29.6 (+0.029); `Temp_cur`=26.0 (+0.019); `DO_slope12`=-0.59 (-0.017)
- model correction -0.035 on top of the anchor 27.00: `Temp_cur`=27.0 (-0.186); `hour_cos`=-0.75 (+0.155); `hour_sin`=-0.66 (-0.053); `Temp_max4`=27.0 (+0.043); `Temp_std4`=0.2 (+0.030)

**salt-marsh ponds: Temp 30 min ahead**
- model correction -0.115 on top of the anchor 1.91: `Temp_slope6`=-0.35 (-0.075); `hour_sin`=0.97 (+0.060); `hour_cos`=-0.26 (-0.049); `Temp_yday_tgt_h1`=5.57 (-0.033); `Temp_d1`=5.72 (-0.027)
- model correction +0.416 on top of the anchor 5.57: `hour_cos`=-0.97 (+0.254); `Temp_slope6`=0.6 (+0.110); `hour_sin`=0.26 (+0.034); `Temp_yday_tgt_h1`=5.23 (-0.030); `Temp_d1`=4.66 (-0.026)

**salt-marsh ponds: Temp 6 h ahead**
- model correction +2.193 on top of the anchor 7.21: `anchor_gap`=-2.22 (+1.246); `Temp_d1`=8.65 (+0.768); `hour_sin`=-0.71 (-0.492); `Temp_slope6`=0.72 (+0.337); `Temp_yday_tgt_h12`=7.21 (+0.322)
- model correction -0.419 on top of the anchor 1.65: `Temp_d1`=3.28 (+0.909); `hour_cos`=0.87 (-0.720); `hour_sin`=0.5 (+0.249); `anchor_gap`=0.25 (+0.236); `Temp_slope6`=-0.26 (-0.220)

**salt-marsh ponds: Temp 1 h ahead**
- model correction +0.015 on top of the anchor 7.05: `hour_cos`=0.5 (-0.182); `hour_sin`=0.87 (+0.097); `Temp_yday_tgt_h2`=3.08 (-0.072); `Temp_slope6`=0.03 (+0.071); `Temp_lag1`=7.03 (+0.026)
- model correction +0.020 on top of the anchor 4.48: `hour_cos`=0.26 (-0.232); `Temp_slope6`=0.14 (+0.159); `hour_sin`=0.97 (+0.138); `Temp_yday_tgt_h2`=4.28 (-0.076); `Temp_std2`=0.1 (-0.046)

## Limits
- Explanations describe the model, not causes in the pond.
- Correlated inputs share attribution, so single-feature rankings are less stable than family shares.
- Faithfulness is tested by replacing inputs with training medians, which can create unusual input combinations.
- Only cells where a model helped were explained; the 4 held-out pond groups are 1 to 4 ponds each, so stability across groups is coarse.