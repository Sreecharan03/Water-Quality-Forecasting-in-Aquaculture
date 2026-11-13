# Evaluation Protocol (DRAFT; frozen only after the student writes `APPROVED PHASE 4`)

Split version `sp-2dd59e32cff4` (features `ft-30c94e8fe1bd`, processed data `pp-682986049e51`).
Assignment content hash: `bb7a56019fc5f84556b3b7b8d573abd44827e369d81e4a552bb4571e897e8cae`.
Machine-readable summary: [splits/split_manifest.json](splits/split_manifest.json). Row-level assignments live only on the Modal volume.

## 1. Time windows (shared by all ponds, calendar midnights IST)
| Window | Origins | Purpose |
|---|---|---|
| train | up to 2026-01-10 00:00 | fit models |
| embargo | next 12 h | dropped |
| validation | until 2026-01-20 00:00 | model selection and tuning |
| embargo | next 12 h | dropped |
| test | after that, to 2026-01-30 | sealed final evaluation |

Embargo = 12 h = longest lookback (6 h) + longest horizon (6 h). Measured gaps: no training target window touches a validation feature window, and the same holds from validation to test.
All ponds use the same cutoffs so that unseen-pond evaluation cannot benefit from other ponds' readings taken on the same days (shared weather).

## 2. Ponds
- **Sealed unseen-pond test ponds (4):** `ara2_3ed4df8e`, `ara2_45e1cde5`, `ara2_b3d128ac`, `ara2_d52ddb31`. Drawn at random (seed 20261113) from 15 eligible ponds before any model existed. Their data before the test window is never used for fitting, selection, imputation statistics, feature selection or SHAP background.
- **Development ponds (13)** in 4 grouped folds; `ara2_858b914c` (data ends 24 Dec) is training-only.

## 3. Evaluation regimes
| Regime | Train on | Evaluate on | Use |
|---|---|---|---|
| dev_future_seen_ponds | dev ponds, train window | same ponds, validation window | model selection |
| dev_future_unseen_fold k (k=0..3) | other dev ponds, train window | held-out pond group, validation window | model selection and pond-generalization gap |
| diagnostic_unseen_sametime_fold k | other dev ponds, train window | held-out pond group, **same** (train) window | diagnostic only, optimistic (shared weather); never for selection |
| FINAL_seen_ponds_future | dev ponds, train + validation | dev ponds, test window | one-time final result |
| FINAL_unseen_ponds_future | dev ponds, train + validation | 4 sealed ponds, test window | one-time final result |

## 4. Rules
1. Everything fitted (imputation values, scalers, feature selection, SHAP background, hyperparameters) uses only the training rows of that regime.
2. Hyperparameter search and failed-model debugging touch only the validation regimes. Test windows are never read for any purpose before the final run.
3. The two FINAL regimes are run once, on the approved finalist(s) only. If any test contamination occurs it will be disclosed and a new protocol built before claiming generalization.
4. Replay inference only: a prediction at time `t` uses data at or before `t`.

## 5. Metrics and uncertainty (per target and horizon)
- Primary: MAE in native units (mg/L, pH units, °C). Also RMSE and MASE against persistence (scale from training rows).
- Baselines: persistence, seasonal naive (daily cycle), ridge on lags. A model "wins" only if it beats persistence with a confidence interval that excludes zero.
- Generalization gap = MAE on unseen ponds minus MAE on seen ponds (same future window).
- Confidence intervals: blocked bootstrap over (pond x calendar day) blocks (`block_day` column), never IID rows. Paired comparisons for pipeline differences.
- Multiple seeds for stochastic models; report spread.

## 6. Hypothesis comparisons (fixed now)
H1 forecast accuracy and H2/H3 explanation stability/faithfulness compare a quality-aware pipeline with an identical quality-blind one (same splits, seeds and tuning budget; the only difference is the quality feature group). A null or negative result is reported as such.

## 7. Disclosures and limits
- Phases 1 to 3 produced descriptive statistics pooled over all ponds and dates, including the sealed ponds and windows (data profile, calibration check, temperature check, feature informativeness on the first 50% of each pond's timeline). No model was fitted and no rule was changed using them. The manual-review examples in Phase 2 happened to include two sealed ponds (`45e1cde5`, `b3d128ac`, 18 Jan, in the unused validation period).
- The public data has no farm or cluster identifier, so held-out ponds may share a farm or microclimate with training ponds. "Unseen pond" does not mean independent farm.
- The unseen test has 4 ponds and about 10 days each (3,900 origins). With about 40 pond-day blocks, intervals will be wide.
- The test window is later and cooler than training. Tree models cannot extrapolate beyond the temperature range seen in training; we will report that explicitly.
- One winter season only.
