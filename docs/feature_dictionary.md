# Feature dictionary (`ft-30c94e8fe1bd`)

Origin time `t` = a recorded 15-minute row. Every feature uses only data at or before `t`. Targets are the real, valid reading at `t + h` for h in ['15 min', '60 min', '360 min']; if no valid reading exists at that time the target is empty (never interpolated).

Groups: **history** (current and lagged readings), **rolling** (trailing statistics), **quality** (data-quality context; the quality-aware pipeline uses these), **time** (clock).

| feature | group | meaning | unit | window | why it is valid at prediction time |
|---|---|---|---|---|---|
| `DO_cur` | history | Latest dissolved oxygen reading at the origin time | mg/L | origin | the origin reading itself is known at t |
| `DO_lag1` | history | dissolved oxygen reading 15 min before the origin | mg/L | t-15 min | past reading |
| `DO_lag2` | history | dissolved oxygen reading 30 min before the origin | mg/L | t-30 min | past reading |
| `DO_lag4` | history | dissolved oxygen reading 1 h before the origin | mg/L | t-1 h | past reading |
| `DO_lag8` | history | dissolved oxygen reading 2 h before the origin | mg/L | t-2 h | past reading |
| `DO_lag12` | history | dissolved oxygen reading 3 h before the origin | mg/L | t-3 h | past reading |
| `DO_lag24` | history | dissolved oxygen reading 6 h before the origin | mg/L | t-6 h | past reading |
| `DO_mean4` | rolling | mean of valid dissolved oxygen readings over the last 1 h | mg/L | last 1 h | uses only readings at or before the origin time |
| `DO_min4` | rolling | min of valid dissolved oxygen readings over the last 1 h | mg/L | last 1 h | uses only readings at or before the origin time |
| `DO_max4` | rolling | max of valid dissolved oxygen readings over the last 1 h | mg/L | last 1 h | uses only readings at or before the origin time |
| `DO_std4` | rolling | std of valid dissolved oxygen readings over the last 1 h | mg/L | last 1 h | uses only readings at or before the origin time |
| `DO_mean12` | rolling | mean of valid dissolved oxygen readings over the last 3 h | mg/L | last 3 h | uses only readings at or before the origin time |
| `DO_min12` | rolling | min of valid dissolved oxygen readings over the last 3 h | mg/L | last 3 h | uses only readings at or before the origin time |
| `DO_max12` | rolling | max of valid dissolved oxygen readings over the last 3 h | mg/L | last 3 h | uses only readings at or before the origin time |
| `DO_std12` | rolling | std of valid dissolved oxygen readings over the last 3 h | mg/L | last 3 h | uses only readings at or before the origin time |
| `DO_mean24` | rolling | mean of valid dissolved oxygen readings over the last 6 h | mg/L | last 6 h | uses only readings at or before the origin time |
| `DO_min24` | rolling | min of valid dissolved oxygen readings over the last 6 h | mg/L | last 6 h | uses only readings at or before the origin time |
| `DO_max24` | rolling | max of valid dissolved oxygen readings over the last 6 h | mg/L | last 6 h | uses only readings at or before the origin time |
| `DO_std24` | rolling | std of valid dissolved oxygen readings over the last 6 h | mg/L | last 6 h | uses only readings at or before the origin time |
| `DO_slope12` | rolling | Linear trend of dissolved oxygen over the last 3 h | mg/L per hour | last 3 h | uses only readings at or before the origin time |
| `DO_age` | quality | Time since the last valid dissolved oxygen reading (capped at 24 h), in 15-min steps | steps | since last valid | uses only readings at or before the origin time |
| `DO_valid_frac24` | quality | Share of the last 6 h with a valid dissolved oxygen reading | fraction | last 6 h | uses only readings at or before the origin time |
| `pH_cur` | history | Latest pH reading at the origin time | pH units | origin | the origin reading itself is known at t |
| `pH_lag1` | history | pH reading 15 min before the origin | pH units | t-15 min | past reading |
| `pH_lag2` | history | pH reading 30 min before the origin | pH units | t-30 min | past reading |
| `pH_lag4` | history | pH reading 1 h before the origin | pH units | t-1 h | past reading |
| `pH_lag8` | history | pH reading 2 h before the origin | pH units | t-2 h | past reading |
| `pH_lag12` | history | pH reading 3 h before the origin | pH units | t-3 h | past reading |
| `pH_lag24` | history | pH reading 6 h before the origin | pH units | t-6 h | past reading |
| `pH_mean4` | rolling | mean of valid pH readings over the last 1 h | pH units | last 1 h | uses only readings at or before the origin time |
| `pH_min4` | rolling | min of valid pH readings over the last 1 h | pH units | last 1 h | uses only readings at or before the origin time |
| `pH_max4` | rolling | max of valid pH readings over the last 1 h | pH units | last 1 h | uses only readings at or before the origin time |
| `pH_std4` | rolling | std of valid pH readings over the last 1 h | pH units | last 1 h | uses only readings at or before the origin time |
| `pH_mean12` | rolling | mean of valid pH readings over the last 3 h | pH units | last 3 h | uses only readings at or before the origin time |
| `pH_min12` | rolling | min of valid pH readings over the last 3 h | pH units | last 3 h | uses only readings at or before the origin time |
| `pH_max12` | rolling | max of valid pH readings over the last 3 h | pH units | last 3 h | uses only readings at or before the origin time |
| `pH_std12` | rolling | std of valid pH readings over the last 3 h | pH units | last 3 h | uses only readings at or before the origin time |
| `pH_mean24` | rolling | mean of valid pH readings over the last 6 h | pH units | last 6 h | uses only readings at or before the origin time |
| `pH_min24` | rolling | min of valid pH readings over the last 6 h | pH units | last 6 h | uses only readings at or before the origin time |
| `pH_max24` | rolling | max of valid pH readings over the last 6 h | pH units | last 6 h | uses only readings at or before the origin time |
| `pH_std24` | rolling | std of valid pH readings over the last 6 h | pH units | last 6 h | uses only readings at or before the origin time |
| `pH_slope12` | rolling | Linear trend of pH over the last 3 h | pH units per hour | last 3 h | uses only readings at or before the origin time |
| `pH_age` | quality | Time since the last valid pH reading (capped at 24 h), in 15-min steps | steps | since last valid | uses only readings at or before the origin time |
| `pH_valid_frac24` | quality | Share of the last 6 h with a valid pH reading | fraction | last 6 h | uses only readings at or before the origin time |
| `Temp_cur` | history | Latest water temperature reading at the origin time | °C | origin | the origin reading itself is known at t |
| `Temp_lag1` | history | water temperature reading 15 min before the origin | °C | t-15 min | past reading |
| `Temp_lag2` | history | water temperature reading 30 min before the origin | °C | t-30 min | past reading |
| `Temp_lag4` | history | water temperature reading 1 h before the origin | °C | t-1 h | past reading |
| `Temp_lag8` | history | water temperature reading 2 h before the origin | °C | t-2 h | past reading |
| `Temp_lag12` | history | water temperature reading 3 h before the origin | °C | t-3 h | past reading |
| `Temp_lag24` | history | water temperature reading 6 h before the origin | °C | t-6 h | past reading |
| `Temp_mean4` | rolling | mean of valid water temperature readings over the last 1 h | °C | last 1 h | uses only readings at or before the origin time |
| `Temp_min4` | rolling | min of valid water temperature readings over the last 1 h | °C | last 1 h | uses only readings at or before the origin time |
| `Temp_max4` | rolling | max of valid water temperature readings over the last 1 h | °C | last 1 h | uses only readings at or before the origin time |
| `Temp_std4` | rolling | std of valid water temperature readings over the last 1 h | °C | last 1 h | uses only readings at or before the origin time |
| `Temp_mean12` | rolling | mean of valid water temperature readings over the last 3 h | °C | last 3 h | uses only readings at or before the origin time |
| `Temp_min12` | rolling | min of valid water temperature readings over the last 3 h | °C | last 3 h | uses only readings at or before the origin time |
| `Temp_max12` | rolling | max of valid water temperature readings over the last 3 h | °C | last 3 h | uses only readings at or before the origin time |
| `Temp_std12` | rolling | std of valid water temperature readings over the last 3 h | °C | last 3 h | uses only readings at or before the origin time |
| `Temp_mean24` | rolling | mean of valid water temperature readings over the last 6 h | °C | last 6 h | uses only readings at or before the origin time |
| `Temp_min24` | rolling | min of valid water temperature readings over the last 6 h | °C | last 6 h | uses only readings at or before the origin time |
| `Temp_max24` | rolling | max of valid water temperature readings over the last 6 h | °C | last 6 h | uses only readings at or before the origin time |
| `Temp_std24` | rolling | std of valid water temperature readings over the last 6 h | °C | last 6 h | uses only readings at or before the origin time |
| `Temp_slope12` | rolling | Linear trend of water temperature over the last 3 h | °C per hour | last 3 h | uses only readings at or before the origin time |
| `Temp_age` | quality | Time since the last valid water temperature reading (capped at 24 h), in 15-min steps | steps | since last valid | uses only readings at or before the origin time |
| `Temp_valid_frac24` | quality | Share of the last 6 h with a valid water temperature reading | fraction | last 6 h | uses only readings at or before the origin time |
| `flag_do_now` | quality | Any FWI DO quality flag on the origin reading (<0.1, jump>2, >10 before noon) | 0/1 | origin | flag rules use values at or before t |
| `flag_ph_now` | quality | Any FWI pH quality flag on the origin reading | 0/1 | origin | flag rules use values at or before t |
| `flag_gap_now` | quality | Origin reading came after a recording gap > 20 min | 0/1 | origin | gap measured to the previous row |
| `n_flag_do_24` | quality | Number of DO-flagged readings in the last 6 h | count | last 6 h | uses only readings at or before the origin time |
| `n_flag_ph_24` | quality | Number of pH-flagged readings in the last 6 h | count | last 6 h | uses only readings at or before the origin time |
| `n_flag_gap_24` | quality | Number of gap-flagged readings in the last 6 h | count | last 6 h | uses only readings at or before the origin time |
| `present_frac24` | quality | Share of the last 6 h time slots that have any recorded row | fraction | last 6 h | uses only readings at or before the origin time |
| `steps_since_prev_row` | quality | Time since the previous recorded row (1 = normal 15-min cadence) | steps | previous row | past rows only |
| `hour_sin` | time | Sine of the time of day (IST), so 23:45 is close to 00:00 | unitless | origin | clock time of the origin |
| `hour_cos` | time | Cosine of the time of day (IST) | unitless | origin | clock time of the origin |

## Targets

- `y_DO_h1`: valid dissolved oxygen reading (mg/L) 15 min after the origin
- `y_pH_h1`: valid pH reading (pH units) 15 min after the origin
- `y_Temp_h1`: valid water temperature reading (°C) 15 min after the origin
- `y_DO_h4`: valid dissolved oxygen reading (mg/L) 1 h after the origin
- `y_pH_h4`: valid pH reading (pH units) 1 h after the origin
- `y_Temp_h4`: valid water temperature reading (°C) 1 h after the origin
- `y_DO_h24`: valid dissolved oxygen reading (mg/L) 6 h after the origin
- `y_pH_h24`: valid pH reading (pH units) 6 h after the origin
- `y_Temp_h24`: valid water temperature reading (°C) 6 h after the origin