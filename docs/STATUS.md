# Project status (updated 2026-11-14)

## Done and approved (pushed to research/init, last pushed commit b22fb95)
Phases 0 to 5.

## Approved on 2026-11-14 ("push") and pushed in two commits
| Item | Result in one line | Review pack |
|---|---|---|
| Phase 5b: anchored-residual LightGBM | Beats both simple guesses in 5 of 9 cells (oxygen all horizons; temperature 1 h, 6 h). pH and temperature 15 min: no. | docs/phases/PHASE_05b.md |
| Phase 6: ranges and low-oxygen alert | Ranges cover about 90% on unseen ponds in all 9 cells. Alert beats three simple baselines in all 3 windows, but is poorly calibrated and gives many false alarms at 30%. | docs/phases/PHASE_06.md |

## In progress
Phase 6b: calibrate the alert probabilities and choose the alert level with a pre-registered rule (one round, validation-side only).

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
