# PHASE 5 — Baselines and LightGBM / XGBoost (REVIEW PACK)

**Date:** 2026-11-13 | **Status:** APPROVED by human (GATE 5), committed.

```
PHASE: 5, Statistical baselines and LightGBM/XGBoost (validation-side only)
OBJECTIVE: Find out honestly whether trained models beat simple forecasts, with fixed settings and no tuning.
DELIVERED: aquatic_xai/models/{baselines,tabular}.py, aquatic_xai/experiments/{run,evaluate}.py, configs/models.yaml,
           modal_jobs/phase5.py, tests/test_models.py, docs/experiments/exp-a0a394b0d781_leaderboard.md
MODAL RUNS: 81 tasks (9 regimes x 3 targets x 3 horizons) fanned out in parallel; coordinator + analysis + reproducibility check
EXPERIMENT: exp-a0a394b0d781 | split sp-2dd59e32cff4 | features ft-30c94e8fe1bd | models: persistence, seasonal naive, ridge, LightGBM, XGBoost
            each trained quality-blind and quality-aware; 3 seeds for LightGBM/XGBoost
TESTS: 35 passed, 0 failed, 0 skipped (remote; 7 new). Same task in two separate containers: max difference 0.0 in every model.
METRICS: see leaderboard; validation-side only. Sealed test windows and the 4 sealed ponds were NOT used.
COST / RESOURCES: 2,016 container-seconds on 2 CPU cores each (about 1.1 core-hours), no GPU. Billing not readable from the CLI: please check the Modal dashboard.
SCIENTIFIC CHECK: no leakage found; one design weakness found (see "What went wrong"); results are mixed.
GITHUB: research/init at 9a17e10 (Phase 4). Phase 5 NOT committed (awaiting approval). The code was run before commit, so the manifest records the Phase 4 SHA plus "uncommitted".
DECISION REQUIRED: APPROVED / REJECTED / REQUEST CHANGES
NEXT PHASE (BLOCKED): see recommendation below
```

## Headline (unseen ponds, future days; average miss with 95% interval, blocks = pond x day)
| Target | Ahead | "same as now" | "same time yesterday" | Best trained model | Verdict |
|---|---|---|---|---|---|
| Oxygen (mg/L) | 15 min | 0.509 | 2.082 | LightGBM aware 0.467 [0.432, 0.502] | beats "same as now" by +8% (clear) |
| | 1 h | 1.209 | 2.083 | LightGBM aware 0.936 [0.881, 0.992] | beats it by +23% (clear) |
| | 6 h | 4.792 | 2.060 | XGBoost blind 2.093 [1.958, 2.232] | beats "same as now" by +56%, **ties "yesterday"** |
| pH | 15 min | 0.035 | 0.078 | ridge 0.040 | **worse** than "same as now" |
| | 1 h | 0.050 | 0.077 | LightGBM blind 0.049 | no clear difference |
| | 6 h | 0.134 | 0.077 | LightGBM blind 0.097 | beats "same as now" but **clearly worse than "yesterday"** (-26%) |
| Temperature (°C) | 15 min | 0.127 | 0.498 | ridge 0.151 | **worse** than "same as now" |
| | 1 h | 0.240 | 0.496 | LightGBM aware 0.224 | no clear difference |
| | 6 h | 0.834 | 0.487 | ridge 0.430 | beats "same as now" by +49%; no clear difference from "yesterday" |

## What this means in plain words
1. **For oxygen, the models help at 15 minutes and 1 hour** (8% and 23% smaller average miss). That is a real but modest gain.
2. **For pH and temperature at 15 minutes, our trained models are worse than just repeating the last reading.**
3. **At 6 hours, the daily cycle does most of the work.** "Same time yesterday" is as good as the trained models for oxygen and temperature, and clearly better for pH on unseen ponds.
4. **Pond shift costs accuracy.** On ponds never seen in training, oxygen error is higher by 0.02 mg/L at 15 min, 0.08 at 1 h and 0.26 at 6 h (all clearly above zero).
5. **Quality-aware vs quality-blind: no consistent benefit.** Aware is slightly better for oxygen at 15 min with LightGBM/XGBoost (about 0.015 to 0.02 mg/L, roughly 4% of the error) and slightly worse for ridge in several cells. With 54 intervals, a few will exclude zero by chance at the 95% level. **Hypothesis H1 is not supported so far.**
6. **Low-oxygen cases are hard.** In the lowest 10% of oxygen values, "same as now" beats the trained models at 15 min and 1 h; at 6 h the models are better (1.5 vs 2.8 mg/L) but still miss by about 1.5 mg/L.
7. **Seeds are stable:** median seed-to-seed spread 1.1% of error, worst 4.6%.

## What went wrong, and why (honest)
- **Design weakness:** our models predict the *absolute* value. At 15 minutes the value barely changes, so a model that must re-create the level from scratch loses to "same as now". The standard fix is to predict the *change* from the last reading. I have **not** tried it, because switching after seeing results is a new experiment that should be agreed first.
- **Missing information for unseen ponds:** the inputs cover only the last 6 hours. "Same time yesterday" wins at 6 hours because it knows that pond's own daily pattern. We could give the model that information (yesterday's value at the target time, yesterday's daily min/max) as new past-only features.
- **Distribution shift:** on future days the temperature error is much larger than on training-period days for the same ponds (LightGBM 6 h: 0.439 vs 0.285). Part of the validation period is cooler than training (seen in Phase 2). The same risk applies to the final test.
- **My own analysis slip (fixed):** the first leaderboard compared models only with "same as now" and hid the "yesterday" result. I added the comparison before presenting.

## Checks that passed
- Rebuilding the same task in two separate containers gives bit-identical errors.
- Persistence and seasonal naive use only values at or before the origin (hand-computed unit tests).
- Ridge imputation and scaling are fitted on training rows only (unit-tested).
- Quality-blind and quality-aware differ only by the quality feature group (unit-tested).
- Confidence intervals resample whole pond-day blocks.

## Recommendation for Gate 5
1. **Do NOT start the GRU/TCN (Phase 6) now.** The problem is not that trees cannot model time. It is that the models lack the daily pattern and are predicting levels instead of changes. A neural net would cost more and would not fix either.
2. **Run one pre-agreed follow-up ("Phase 5b"), validation-side only, cheap CPU:**
   - A: predict the **change** from the last reading instead of the level.
   - B: add **past-only daily-pattern features**: the reading one day before the target time, and yesterday's min, max and mean. This needs a new feature version (the split stays identical because origins and targets do not change; I will verify the assignment hash).
   - Success rule written down now: a variant is kept only if it beats "same as now" AND "same time yesterday" with a 95% interval above 0 on unseen ponds for at least one target and horizon, and does not get worse elsewhere.
3. **Tuning budget: not yet.** Fixed settings are close enough that tuning will not change the story; the gaps are about information and framing.
4. Hypothesis H1 (quality-aware helps) is currently **not supported**; we keep testing it in 5b and report the result either way.

## Guide explanation
1. We compared simple guesses with LightGBM and XGBoost on days and ponds the models had not trained on.
2. For oxygen, the models help a little at 15 minutes and a good amount at 1 hour.
3. For pH and temperature at short range, repeating the last reading is as good or better.
4. At 6 hours, "same time yesterday" is a very strong guess that our models only match.
5. Adding data-quality information did not help consistently, and we report that plainly.

## Decisions I need from you
1. Accept these results as the Gate 5 baseline (or request changes).
2. Approve the "Phase 5b" follow-up above with its success rule, or tell me to skip it.
3. Confirm: no GPU / no tuning budget yet.
