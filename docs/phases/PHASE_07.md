# PHASE 7: SHAP explanations (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** Committed under the standing instruction "complete all the phases" (change requests still welcome).

```
PHASE: 7, exact TreeSHAP explanations of every model that was shown to help (validation-side only)
OBJECTIVE: Show what the forecasting models and the low-oxygen alert actually use.
DELIVERED: configs/explain.yaml (contract written BEFORE any SHAP value), aquatic_xai/explain/{shap_utils,run}.py, modal_jobs/{loaders,phase7}.py,
           tests/test_explain.py, docs/experiments/exp-570e678b7197_explanations.md
EXPERIMENT: exp-570e678b7197 | 11 explained cells (Eluru: oxygen 15 min / 1 h / 6 h, temperature 1 h / 6 h, alert 1 h / 3 h / 6 h; salt marsh: temperature 30 min / 1 h / 6 h) x 5 regimes x 3 seeds = 55 tasks
TESTS: 59 passed on Modal (4 new; SHAP additivity and deletion control unit-tested). Same task in two containers: max SHAP difference 0.0.
COST: CPU only, no GPU. Sealed ponds and test windows not used.
```

## What the models use (plain words)
- **Short range (15 min, 1 h):** the latest readings (oxygen now, its last few lags, 1 h range) and the **time of day** (`hour_cos`) carry most of the explanation. Oxygen now is the top input for the low-oxygen alert at 1 h (mean abs SHAP 1.63 log-odds).
- **6 h ahead:** the **pond's own daily pattern** takes over. For oxygen the top inputs are the gap between yesterday's value and now, time of day, and yesterday's value at the target time. Daily-pattern inputs carry 39% of the oxygen attribution and 38% of the temperature attribution at Eluru (31% in the salt marsh).
- **Low-oxygen alert at 6 h:** the top input is **the minimum oxygen in the same window yesterday** (mean abs SHAP 1.00), then oxygen now, time of day, and the pond's lowest oxygen in the last 24 h. In words: the model learned "ponds that crashed at this time yesterday tend to crash again tonight, and a low overnight minimum raises the risk".
- **Temperature:** time of day and yesterday's temperature dominate at 6 h; time of day dominates at 1 h in both datasets. The salt marsh leans more on trend (`Temp_slope6`), Eluru more on the latest reading.

## Pre-registered expectations (descriptive)
| Expectation | Result |
|---|---|
| X1: at 6 h the daily-pattern family carries at least 25% (oxygen, temperature) | **Met in all 3 cells** (39%, 38%, 31%) |
| X2: at the shortest horizon the history family carries at least 50% | **Not met** in all 3 cells (42%, 41%, 15%); rolling and time-of-day inputs share the load |
| X3: for temperature, time of day is among the top 3 families | Met in 3 of 5 cells (at 1 h and short range); not met at 6 h, where yesterday's temperature and the anchor gap dominate |

## Cautions (stated plainly)
- SHAP describes the **model**, not the pond. "Temperature level over 24 h" appears in the alert's top inputs; it may stand in for pond identity or season rather than a physical effect.
- Correlated inputs (for example `DO_cur`, `DO_mean4`, `DO_max4`) share attribution, so single-input rankings are less stable than family shares.
- A few example rows (without pond names or times) are in the experiment report; they show signed contributions for the alert and forecasts.

## Decisions I need
Accept Phase 7 as the explanation baseline, or request changes. Phase 8 (are these explanations trustworthy?) is in `PHASE_08.md`.
