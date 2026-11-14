# PHASE 6: Forecast ranges and low-oxygen early warning (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** APPROVED by human (GATE 6, "push"), committed after Phase 5b.

```
PHASE: 6, uncertainty ranges (conformal prediction) + low-oxygen early warning (validation-side only)
OBJECTIVE: Give every forecast an honest range, and warn about severe low oxygen, tested on ponds the model never saw.
DELIVERED: configs/phase6.yaml (contract written BEFORE running), aquatic_xai/uncertainty/conformal.py,
           aquatic_xai/alerts/{labels,run,evaluate}.py, modal_jobs/phase6.py, tests/test_alerts_conformal.py,
           docs/experiments/exp-bad07bab4b89_phase6_results.md
EXPERIMENT: exp-bad07bab4b89 | split sp-2dd59e32cff4 (hash identical) | features ft-30c94e8fe1bd + daily-v1
            ranges reuse the Phase 5b predictions (exp-1e0c9c9e8164); alerts = 15 new LightGBM classifier tasks, seeds 0-2
TESTS: 46 passed (7 new). Alert labels re-derived independently for 1,530 sampled (origin, window) pairs: 0 mismatches.
       Yesterday-window feature rebuilt from truncated history: 1,530 checks, 0 mismatches. Same task in two containers: max difference 0.0.
COST: CPU only, no GPU. Billing not readable from the CLI: please check the Modal dashboard.
SCIENTIFIC CHECK: no leakage found; ranges and alerts judged against rules fixed in configs/phase6.yaml before any model ran.
GITHUB: Phases 5b and 6 committed after approval (see git log).
```

## Choice made before running (from counts only, no model)
Low oxygen is very common in this data: **21% of readings are below 3 mg/L and 13% below 2 mg/L**. A 3 mg/L alert would fire almost all the time, so the alert uses the severe level, **2.0 mg/L**. Only these descriptive counts (dev_train and dev_val, no model, no test data) informed the choice.

## A. Forecast ranges (90% target), unseen ponds
Range = prediction ± q, where q comes from errors on three other pond groups (never the pond group being tested).

| target | 15 min | 1 h | 6 h |
|---|---|---|---|
| Oxygen (mg/L) | ±1.11 | ±2.15 | ±3.99 |
| pH | ±0.067 | ±0.105 | ±0.170 |
| Temperature (°C) | ±0.27 | ±0.48 | ±0.89 |

- **Coverage was 88.9% to 89.9% in all 9 cells** (target 90%), so the 9 of 9 pass the pre-registered rule.
- For oxygen at 1 h and 6 h, and temperature at 1 h and 6 h, the plain ranges were too narrow in the daytime (82 to 85%) and too wide at night (94 to 98%). The rule then picks the **day/night variant**, which gives about 90% in both.
- Models make ranges narrower where they beat the simple guess: oxygen 6 h ±3.99 vs ±9.69 for "same as now"; temperature 6 h ±0.89 vs ±1.85; pH 6 h ±0.17 vs ±0.28.

## B. Low-oxygen alert (< 2.0 mg/L within the next 1 h / 3 h / 6 h), unseen ponds
Average precision (AP) means "how well are real events ranked above non-events" (1.0 = perfect). The event rate is 17%, 23% and 32%.

| window | model | yesterday's window | trend | current level | verdict |
|---|---|---|---|---|---|
| 1 h | 0.945 | 0.578 | 0.923 | 0.937 | PASS (but only +0.009 over "current level", interval +0.000 to +0.018) |
| 3 h | 0.894 | 0.620 | 0.735 | 0.871 | PASS (+0.023 over "current level") |
| 6 h | 0.863 | 0.667 | 0.642 | 0.813 | PASS (+0.051 over "current level") |

All three pass the pre-registered rule (99% interval above 0 against all three baselines).

## What went well
- The ranges are honest: they contain the truth about 90% of the time on ponds the model never saw.
- The alert beats all three simple baselines in all three windows, and the gain over "current level" grows with the window (from +0.009 to +0.051).

## What is not good enough yet (honest)
1. **Oxygen ranges at 6 h are very wide (±4 mg/L).** At 90% confidence that says little. They are honest but not very useful at long range.
2. **pH and temperature ranges vary a lot between pond groups** (per-fold coverage 62% to 100%), because each group has only 3 to 4 ponds. The pooled number is right on average, but one group of ponds can be far from 90%.
3. **At 1 h the alert barely beats "current level"** (+0.009). Most of the 1 h signal is simply "oxygen is already low".
4. **Probabilities are not well calibrated.** At 6 h, predictions of 0 to 10% are right about 9% of the time (it under-warns), and predictions of 70 to 90% are right only 70% of the time (it over-states). Brier score 0.032 / 0.065 / 0.114.
5. **At the fixed alert level (P ≥ 0.30, 6 h) the model is not clearly better than the best simple rule.** It caught 58 of 76 episodes (76%) with a median 5.25 h warning, but a false alarm appeared on 60% of pond-days. "Same window yesterday", given the same recall, caught the same 58 with 56% false-alarm days and 5.88 h warning. So the practical case for the model rests on better ranking (AP), not on this operating point. A farmer-ready alert would need a better-chosen operating point, which I did not tune (one round, as agreed).
6. Only 76 episodes lie inside the evaluation windows, so the episode view is descriptive.
7. Calibration for the ranges uses the same validation days as the test days (different ponds). Pond groups share weather, so coverage may be a little optimistic for future days.

## Recommendation
- Adopt the day/night ranges in the app for all 9 cells, and show the low-oxygen alert as a **probability with a plain warning when it is above 30%**, labelled "experimental" until calibration is improved.
- Next: Phase 7 (SHAP on the anchored LightGBM and on the alert classifier), so we can explain *why* the alert fires. The alert is now a second target that needs explanation.
- A calibration step (for example, rescaling probabilities on other pond groups) is a candidate Phase 6b if you want farmer-ready alerts. It is a new experiment and needs its own plan.

## Guide explanation
1. We gave each forecast a range that is right about 9 times out of 10 on ponds the model never saw, and we checked that claim.
2. We built a low-oxygen warning. It ranks risky moments better than three simple rules, but its false-alarm rate is still high.
3. Both results are honest: some are good, and the weak points are listed above.

## Decisions I need
1. APPROVED PHASE 5b (required before 6 can be committed).
2. APPROVED PHASE 6, or REQUEST CHANGES.
3. Should I plan a calibration step (Phase 6b) before the SHAP phase?
