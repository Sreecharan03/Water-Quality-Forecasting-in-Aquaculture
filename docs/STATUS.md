# Project status (updated 2026-11-14)

## Done and approved (pushed to research/init, phases 0 to 5 at b22fb95; 5b and 6 pushed later, see git log)
Phases 0 to 5.

## Approved on 2026-11-14 ("push") and pushed in two commits
| Item | Result in one line | Review pack |
|---|---|---|
| Phase 5b: anchored-residual LightGBM | Beats both simple guesses in 5 of 9 cells (oxygen all horizons; temperature 1 h, 6 h). pH and temperature 15 min: no. | docs/phases/PHASE_05b.md |
| Phase 6: ranges and low-oxygen alert | Ranges cover about 90% on unseen ponds in all 9 cells. Alert beats three simple baselines in all 3 windows, but is poorly calibrated and gives many false alarms at 30%. | docs/phases/PHASE_06.md |

## Phase 6b (approved 2026-11-14, "push the waiting work")
Alert calibration and alert level. Calibration passes in 2 of 3 windows (6 h fails). The pre-registered decision rule FAILED: the model's false alarms (68% of pond-days) are not lower than 'same window yesterday' (58%). The alert stays experimental; no second round. Review pack: docs/phases/PHASE_06b.md.

## Phase 1b: external data (in progress, on this branch)
- AquaSustain-Bench and AquaSense: REJECTED, released data is synthetic (docs/external_data_decision.md).
- BCO-DMO salt-marsh ponds: gate passed as an out-of-domain test only. Proposed use: replicate the frozen method on its own split (needs your approval of the plan), plus a descriptive zero-shot transfer.
- Open: request more data from the Fish Welfare Initiative.
- Production plan: docs/production_plan.md. CI: .github/workflows/ci.yml (not yet run on GitHub).

## Branches
`research/init` holds Phases 0 to 6 (pushed). `research/phase6b-external-data` holds Phase 6b and Phase 1b work. **Nothing is merged to `main`.**

## Documentation written in this stretch (committed with Phase 6)
README.md, docs/literature_matrix.md (full texts not yet read), docs/model_card.md (draft), this file.

## Still open
- Read the full text of the key papers (matrix rows 1, 6, 9, 10) and repeat the literature search properly.
- Check Modal billing on the dashboard (not readable from the CLI).
- CI (tests on every push).
- Independent experimental-paper review (master prompt requirement).
- Phases 7 to 12: SHAP, explanation checks, app (simple-name inputs in docs/ui_input_spec.md), serving, sealed final test (run once), thesis and viva.
- Licence of the dataset is still unclear (citation only).

## Not decided without you
Anything that touches the sealed test, and any later commit that has not been approved.
