# PHASE 5b: Anchored-residual LightGBM (REVIEW PACK)

**Date:** 2026-11-13 | **Status:** APPROVED by human (GATE 5b, "push"), committed.

```
PHASE: 5b, one results-driven follow-up to Phase 5 (validation-side only)
OBJECTIVE: Fix the two diagnosed weaknesses (levels instead of changes; no daily-pattern information) with ONE model, one round.
DELIVERED: aquatic_xai/features/daily.py, aquatic_xai/models/anchored.py, aquatic_xai/experiments/run_anchored.py,
           configs/anchored.yaml, modal_jobs/phase5b.py, tests/test_anchored.py, 99% option in evaluate.py,
           docs/experiments/exp-1e0c9c9e8164_phase5b_results.md
EXPERIMENT: exp-1e0c9c9e8164 | split sp-2dd59e32cff4 (hash identical) | features ft-30c94e8fe1bd + daily-v1
MODAL RUNS: 45 tasks (5 regimes x 3 targets x 3 horizons), 580 container-seconds on 2 CPU cores each, no GPU
TESTS: 39 passed (4 new). Daily-feature prefix invariance on real tables: 680 origins x 21 features, 0 mismatches.
       Split assignment hash identical to the approved manifest. Same task in two containers: max difference 0.0.
GITHUB: Phase 5b committed after approval (see git log).
```

## Result against the rule written before running (unseen ponds, 99% intervals, must beat BOTH simple guesses)
| Target | 15 min | 1 h | 6 h |
|---|---|---|---|
| Oxygen | PASS (+5.8% vs now) | PASS (+24.8%) | PASS (+62% vs now, +12.6% vs yesterday) |
| pH | fail (12.7% **worse** than now) | fail (not clearly better than now) | fail (not clearly different from yesterday) |
| Temperature | fail (11% **worse** than now) | PASS (+20.9%) | PASS (+51% vs now, +15.9% vs yesterday) |

5 of 9 cells pass. The other 4 fall back to the best simple guess (pH: same as now at 15 min and 1 h, same time yesterday at 6 h; temperature 15 min: same as now). One round only, so no retry.

## Plain words
1. Oxygen is now clearly better than both simple guesses at every horizon. At 6 h the miss is 1.81 mg/L against 2.06 (yesterday) and 4.79 (now).
2. Temperature is clearly better at 1 h and 6 h, but at 15 min nothing beats repeating the last reading.
3. pH: the models still do not beat simple guesses. pH barely moves, so there is little to learn.
4. Versus Phase 5's level model, anchoring helps most at 6 h (oxygen +14%, pH +13%, temperature +6% but not clear) and for temperature at short range (+17%).
5. Quality information: still no consistent benefit. Aware is better for oxygen at 15 min (-0.025 mg/L) and 1 h (-0.013), but worse at 6 h (+0.029). With the rule written in advance, quality-blind is used wherever it passes. **H1 stays not supported overall; there is a small short-range oxygen effect worth one careful look in Phase 8.**

## Honest caveats
- Hard cases (lowest 10% of oxygen): at 15 min and 1 h the model does **not** beat "same as now" (0.25 vs 0.22 at 15 min). At 6 h it is much better (1.43 vs 2.84 now, similar to yesterday's 1.23, not better).
- Seed spread is large in a few tiny-error cells (up to 20% for temperature 1 h in one fold; median 2%). Pooled results are less affected, but those cells are noisy.
- Yesterday's value was missing for 3.1% of evaluation rows and 6.9% of training rows at 6 h (fallback to "same as now").
- 54 intervals are shown; a few borderline ones (DO 6 h vs yesterday lower end +1.5% to +3.6%) are close to zero.
- Distribution shift (cooler future days) remains; the final sealed test carries the same risk.
- The sealed test and sealed ponds were not used.

## Recommendation
- Adopt per-cell choice: anchored LightGBM (quality-blind) for oxygen at all horizons and temperature at 1 h and 6 h; simple guesses for the rest. Do **not** keep trying models for pH now.
- Do not start the GRU/TCN: gains left are small and the weak cells (pH, 15 min) are limited by the data, not model type.
- Next: Phase 7 SHAP on the anchored LightGBM, and the literature matrix/README/model card catch-up.

## Decisions I need
1. APPROVED PHASE 5b (or REQUEST CHANGES).
2. Confirm the per-cell choice above is the model to explain in Phase 7.
