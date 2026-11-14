# Chapter 5: Results (draft; all numbers from the repository reports)

## 5.1 Baselines and standard models (Phase 5, validation, unseen ponds)
On future days and ponds not seen in training, trained models (ridge, LightGBM, XGBoost) helped for oxygen at 15 minutes and 1 hour (8% and 23% smaller average miss than "same as now"), but for pH and temperature at 15 minutes they were **worse** than repeating the last reading. At 6 hours, "same time yesterday" tied or beat the models (for pH on unseen ponds: 0.077 against 0.097). Quality information gave no consistent gain (H1 not supported). Unseen ponds cost accuracy, growing with distance. Seed-to-seed spread was small (median 1.1% of error). Diagnosis: the models predicted levels instead of changes and lacked the daily pattern.

## 5.2 The anchored-residual model (Phase 5b, validation, 99% intervals)
Beats both baselines in **5 of 9** cells: oxygen at all three distances, temperature at 1 hour and 6 hours. Not for pH, and not for temperature at 15 minutes. Example (unseen ponds): oxygen 6 hours, average miss 1.81 mg/L against 2.06 for "yesterday" and 4.79 for "same as now". Quality-aware versus blind: aware better for oxygen at 15 minutes and 1 hour, worse at 6 hours: **H1 remains unsupported overall**. A fallback to the better plain guess is used in failed cells.

## 5.3 Ranges (Phase 6)
Conformal ranges covered 88.9% to 89.9% on unseen ponds in all nine cells. Daytime coverage was too low for four cells (82% to 85%) so a day/night version is used there. Models narrow the ranges where they beat the guesses (oxygen 6 hours: ±3.99 mg/L against ±9.69 for ranges around "same as now"). Per pond-group coverage varied widely for pH and temperature (62% to 100%) because each group has few ponds.

## 5.4 Low-oxygen warning (Phases 6 and 6b)
Average precision beat all three simple rules in all three windows (validation). But: probabilities were not well calibrated; after calibration the 6-hour bins still failed; and when the alert level was chosen on other pond groups to catch 80% of episodes, the model raised false alarms on 68% of pond-days against 58% for "same window yesterday" (difference +9.6 points, 99% interval −2.4 to +22.4). **Pre-registered consequence: the alert stays experimental; no second round.**

## 5.5 Replication on salt-marsh ponds (Phase 1b-R, held-out ponds, winter validation)
Method replicates **weakly** (3 of 9 cells, including a 6-hour cell), but different cells: temperature passes at all three distances (+52%, +53%, +40% over "same as now") while oxygen fails everywhere (worse than "same as now" at 30 minutes and 1 hour; at 6 hours it ties "yesterday"). pH fails. Ranges: 7 of 9 cells pass. The alert test is underpowered (winter validation: 2% to 5% event rate, 36 episodes): 0 of 3 windows pass, but all nine point estimates favour the model. The evaluation method transferred; the oxygen gains did not.

## 5.6 The sealed final test (Phase 11; 4 never-seen ponds, about 10 days; 99% intervals)
| Cell | App | Same as now | Same time yesterday | Verdict |
|---|---|---|---|---|
| Oxygen 15 min | 0.329 | 0.387 | 1.548 | pass |
| Oxygen 1 h | 0.714 | 1.115 | 1.541 | pass |
| Oxygen 6 h | 1.655 | 4.889 | **1.520** | fail |
| Temperature 1 h | 0.098 | 0.143 | 0.206 | pass |
| Temperature 6 h | 0.250 | 0.667 | **0.203** | fail |
**3 of 5 model cells pass.** Ranges never under-covered (91.8% to 99.2%) but were wider than needed (only 1 of 9 meets the literal 87% to 93% rule; the low-value check rests on 381 rows for oxygen, 1 for pH and 0 for temperature). The low-oxygen ranking beat all three simple rules for the next 3 and 6 hours (6 hours: 0.886 against 0.831 for "current level"), but percentages were overstated (0 of 3 windows calibrated) and at the "High chance" level the alert caught 29 of 31 episodes with a false alarm on 98% of pond-days (simple rule at matched recall: 75%).
Consequence applied: the two failed 6-hour cells use "same time yesterday" in the app (`final_v2`); that switch has not itself been re-tested.

## 5.7 Putting it together
| Claim | Supported by | Strength |
|---|---|---|
| Trained models beat plain guesses for oxygen at 15 min and 1 h, and temperature at 1 h, on never-seen ponds | Validation (Phase 5b) and the sealed test | **strong within this dataset** |
| They do so at 6 hours | Validation yes, sealed test no | **not supported** |
| Data-quality features help | Phases 5, 5b | **not supported** |
| Conformal ranges are valid | Phases 6, 11 | **valid but conservative** |
| The alert is usable as an alarm | Phases 6b, 11 | **not supported** |
| The method works elsewhere | Phase 1b-R | **partly** (evaluation transfers; oxygen gains do not) |
