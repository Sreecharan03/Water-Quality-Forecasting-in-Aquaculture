# PHASE 8: Explanation validation (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** Committed under the standing instruction "complete all the phases" (change requests still welcome).

```
PHASE: 8, test whether the explanations are stable and faithful (pre-registered tests E1 to E4, validation-side only)
OBJECTIVE: Decide which explanations can be trusted, using tests fixed before any SHAP value was computed.
DELIVERED: same experiment as Phase 7 (exp-570e678b7197); rules in configs/explain.yaml (phase8_tests)
RESULT: 9 of 11 explanations validated (all four tests must pass)
```

## The four tests
- **E1, same across random seeds:** rank correlation of mean |SHAP| across 3 model seeds at least 0.90.
- **E2, same across pond groups:** mean rank correlation across the 4 held-out pond-group models at least 0.70, and at least 3 of the top-5 inputs shared on average.
- **E3, same across time:** first half versus second half of the validation window, rank correlation at least 0.70.
- **E4, faithful:** replace the top-5 inputs (chosen on training rows, so the choice does not see the test rows) by their training medians; the error must rise by clearly more than when 5 random inputs are replaced (99% interval above 0), in the main model and at least 3 of 4 pond-group models.

## Results
| Cell | E1 | E2 | E3 | E4 | Validated |
|---|---|---|---|---|---|
| Eluru alert 1 h | pass | pass | pass | pass (4/4) | **yes** |
| Eluru alert 3 h | pass | pass | pass | pass (4/4) | **yes** |
| Eluru alert 6 h | pass | pass | pass | pass (3/4) | **yes** |
| Eluru oxygen 15 min | pass | pass | pass | **fail** (2/4) | **no** |
| Eluru oxygen 1 h | pass | pass | pass | pass (4/4) | **yes** |
| Eluru oxygen 6 h | pass | pass | pass | pass (3/4) | **yes** |
| Eluru temperature 1 h | pass | pass | pass | pass (4/4) | **yes** |
| Eluru temperature 6 h | pass | pass | pass | pass (3/4) | **yes** |
| Salt marsh temperature 30 min | **fail** (0.84) | pass | pass | pass (4/4) | **no** |
| Salt marsh temperature 1 h | pass | pass | pass | pass (4/4) | **yes** |
| Salt marsh temperature 6 h | pass | pass | pass | pass (4/4) | **yes** |

## What this means
1. For **9 of 11** cells, the explanations are stable across seeds, pond groups and time, and they are faithful: removing what SHAP calls important hurts the model more than removing random inputs.
2. **Not validated:** Eluru oxygen at 15 min (the main model passes, but only 2 of 4 pond-group models do) and salt-marsh temperature at 30 min (the ranking changes between seeds, correlation 0.84). Their explanations should be shown with a warning, or not shown, in the app.
3. Stability is high where the model beats the simple guesses by a wide margin. It is weaker where the gain is small (Eluru oxygen at 15 min improves on "same as now" by about 6%).
4. The strongest result for the thesis: the **alert's explanations are validated in all three windows**, so the app can say why an alert fired (for example "oxygen was this low at the same time yesterday").

## Limits
Faithfulness is tested with median replacement (can create unusual inputs); the four held-out pond groups are small; stability does not prove a physical cause; the tests were applied once to fixed definitions.

## Decisions I need
Accept the 9 validated explanations for use in the app, and the 2 non-validated ones as "show with warning", or request changes.
