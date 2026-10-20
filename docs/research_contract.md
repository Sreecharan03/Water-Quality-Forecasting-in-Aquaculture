# Research Contract (DRAFT v0 — NOT FROZEN)

Status: draft for student/guide review at Gate 0. Nothing here is frozen until the student replies `APPROVED PHASE 0`, and the target/horizon list is re-confirmed at Gate 1 after real data inventory.

**Title (fixed):** An aquatic model for water quality prediction and interpretation using explainable AI

## 1. Task
Given observations at or before time `t` for pond `p`, forecast the measured value of a target at `t+h`.

| Item | Draft | Status |
|---|---|---|
| Targets | DO (mg/L), pH (dimensionless), water temperature (°C) | Columns stated in the FWI README; units/contents to be verified in Phase 1 |
| Horizons | 15 min (1 step), 1 h (4 steps), 6 h (24 steps) | Provisional; depends on usable uninterrupted windows |
| Truth | An actually observed, non-zero, non-artifact measurement at `t+h` | No interpolated targets |
| Features | Only data at `<= t` | Leakage tests required (Phase 3) |

## 2. Hypotheses (falsifiable)
- **H1 (forecast):** A quality-aware pipeline has lower MAE than an otherwise identical quality-blind pipeline on held-out ponds and on future time blocks.
- **H2 (explanation stability):** Quality-aware models give more stable attribution rankings (Spearman/Kendall across seeds, blocks, ponds) than quality-blind ones.
- **H3 (faithfulness):** Group-level lag ablation (with retraining) agrees with grouped SHAP ranking better than naive per-feature permutation does.
- **Null-result policy:** If H1–H3 are not supported, we report that. We do not relax the test set, drop hard examples, or re-tune after the sealed test.

## 3. Baselines
Persistence; seasonal naive (only if a daily cycle is verified; 96 steps/day at 15 min); ridge on lags; LightGBM; XGBoost. GRU/TCN only if tree-model errors show a real temporal limitation (Gate 5).

## 4. Metrics
Per target and horizon: MAE (native units, primary), RMSE, MASE vs persistence; generalization gap (held-out pond minus in-distribution). Confidence intervals by blocked bootstrap over pond and contiguous time blocks (not IID rows).

## 5. Splits (to be frozen at Gate 4)
Forward-chronological blocks with an embargo >= max lookback + max horizon; unseen-pond group folds; one sealed test used once. Observation span is about 3 months, so only a single season is covered. This must be stated as a limitation.

## 6. Dataset and licence
- Source: `fish-welfare-initiative/Data-Campaign-Data`, 17 pond CSVs, Nov 2025–Jan 2026, Eluru, Andhra Pradesh.
- Licence: README says "shared publicly... Please cite Fish Welfare Initiative." No LICENSE file; GitHub reports none. **Redistribution terms are unclear.** Decision: do not commit raw data to GitHub; cite FWI; optionally ask FWI to confirm terms.
- Zeros are documented equipment artifacts (not flagged by QC rules) and must be handled explicitly.

## 7. Validity threats (initial)
1. ~3 months, one season, 17 ponds: small N of independent units; claims must be narrow.
2. QC flags are rule-based (thresholds on DO/pH jumps) and reproduced from Excel colouring. Some may be computed from the same values they flag, so flag availability at prediction time must be checked.
3. Probe fouling (~5-day cleaning cycle) creates drift not captured by flags.
4. Possible pond reinstall/harvest regimes (e.g. `ara2_ca187575`) break stationarity.
5. The 2025 IEEE paper is a review; it motivates the gap but supplies no method or data to reproduce.
6. SHAP shows model associations, not physical causes.

## 8. Significance plan
Paired blocked-bootstrap differences between pipelines, reported with CIs; no p-hacking across horizons/targets. The list of comparisons is fixed at freeze.
