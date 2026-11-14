# PHASE 11: The sealed final test (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** Run ONCE as you confirmed ("yes do phase 11"). Awaiting your decision on the consequences below.

```
PHASE: 11, the sealed final test of the serving bundle on ponds and days it never saw
CONTRACT: configs/final_test.yaml, committed and pushed (924f35e) BEFORE the sealed rows were read; smoke test and analysis rehearsal run on development data only
MODELS TESTED: models/final_v1 exactly as verified in Phase 10 (file hashes checked by the runner before it would start)
DATA: 4 sealed ponds (ara2_3ed4df8e, ara2_45e1cde5, ara2_b3d128ac, ara2_d52ddb31), test window, 3,900 origins (about 10 days at the end of January);
      secondary: the 13 development ponds, test window, 10,611 origins
RUN: started 2026-11-14 09:09:23 UTC, completed 09:09:32 UTC, one attempt; once-only lock written to the artifact volume
RESULT FILES: docs/experiments/final_test_report.md (full tables)
DISCLOSURES: one re-analysis after the run added a column (rows in the low-value group) to the range table: presentation only, no data touched, no rule changed
```

## The honest headline
The system helped clearly where it was supposed to help most, did **not** hold up at 6 hours, and the alert and range wording need to be more modest than we planned.

## A. Forecasts on never-seen ponds (average miss; lower is better)
| What | Distance | App | "Same as now" | "Same time yesterday" | Verdict (pre-registered rule) |
|---|---|---|---|---|---|
| Oxygen | 15 min | **0.33 mg/L** | 0.39 | 1.55 | **PASS** (+15% over "same as now", clear) |
| Oxygen | 1 h | **0.71** | 1.12 | 1.54 | **PASS** (+36%) |
| Oxygen | 6 h | 1.66 | 4.89 | **1.52** | **fail**: not clearly better than yesterday (-5.6%, interval -25% to +11%) |
| Temperature | 1 h | **0.10 °C** | 0.14 | 0.21 | **PASS** (+32%) |
| Temperature | 6 h | 0.25 | 0.67 | **0.20** | **fail**: clearly worse than yesterday (-20%, interval -50% to -0.2%) |
| pH (all distances) and temperature 15 min | | plain guess | | | no model claimed; the guess used was as good as or better than the other |

**3 of 5 model cells pass. The forecasting is not called fully validated.** The two failures are both at 6 hours, where "same time yesterday" is a very strong competitor on these ponds, as in Phase 5.

## B. Ranges ("likely between")
Coverage on never-seen ponds was **91.8% to 99.2%** in all 9 cells: the ranges never under-covered, but except for oxygen at 6 h they were **wider than necessary** (94% to 99%, against the 90% target), because the test days were calmer than the days they were calibrated on. By the literal rule (87% to 93%, plus at least 85% in the low-value group) only **1 of 9** cells passes. Two further details: the low-value group has 381 rows for oxygen but **1 row for pH and 0 for temperature**, so those checks say nothing; and per-pond coverage for oxygen at 6 h ranged from 79% to 98%.

## C. Low-oxygen chance
- **Ranking:** passes for the next 3 hours and 6 hours against all three simple rules (6 h: average precision 0.886 against 0.831 for "current level"). For the next hour it passes against two rules and is only +0.013 ahead of "trend" (interval -0.001 to +0.035), so it fails the rule by a hair.
- **Percentages:** **0 of 3 windows** are calibrated. The app overstated risk: when it said about 18% in the 6 h window, the real rate was 4%; when it said 9%, 7%. Calibrated probabilities were worse (Brier 0.101) than the raw model output (0.095).
- **As an alarm** (6 h, "High chance" at 31% or more): it caught **29 of 31** episodes (94%) with a median 6 h warning, but it raised a false alarm on **43 of 44 pond-days (98%)**. The simple rule "same window yesterday", at a level matched to the same recall, had false alarms on 75%. So the alert is a risk ranking, not a usable alarm.

## What this means
- **Where the trained models help (never-seen ponds):** oxygen 15 minutes and 1 hour ahead, and temperature 1 hour ahead. These hold in the sealed test.
- **Where they do not:** 6 hours. Yesterday's reading is as good or better.
- **Compared with validation:** oxygen and temperature errors in the test window were mostly **smaller** than in validation (calmer days), so absolute numbers are not comparable across windows; the comparison with plain guesses is what counts.
- Limits of the test itself: 4 ponds, about 10 days, one region, one season.

## What I changed in the app because of the result (and what I did not)
- Built **`models/final_v2`** (verified: hashes, exact parity with the pipeline, out-of-range guard, latency 0.11 s p95). It applies the fallback rule that was fixed in Phase 5b ("a cell whose model does not beat the plain guesses uses the best plain guess") to the two failed 6-hour cells, so the app now uses "same time yesterday" there and says so. Its ranges for those two cells are calibrated on validation errors of that plain guess and have **not been re-tested**.
- Updated the app's evidence and limits text to the final test, including the failures.
- `final_v1` stays untouched as the exact artifact that was tested. `modal_jobs/serve.py` and the runbook now point to `final_v2`.
- I did **not** retrain, tune, drop ponds or change thresholds.

## Decisions I need
1. Accept the final-test results as reported, including the failed cells.
2. Confirm `final_v2` as the bundle the app uses.
3. Move on to Phase 12 (thesis and viva material).
