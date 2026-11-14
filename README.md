# An aquatic model for water quality prediction and interpretation using explainable AI

M.Tech project. Forecast pond water quality (dissolved oxygen, pH, temperature) 15 minutes to 6 hours ahead, give each forecast an honest range, warn about severe low oxygen, and explain the predictions. Everything is tested on **ponds the model has never seen**.

**Status (2026-11-14):** see [docs/STATUS.md](docs/STATUS.md). Phases 0 to 5 are approved and pushed. Phases 5b and 6 are built and awaiting approval.

## Data
Fish Welfare Initiative "Data-Campaign": 17 continuous pond CSVs, 15-minute readings, 2025-11-28 to 2026-01-30, Eluru, India. Licence unclear, so only citation and derived statistics are published. **No raw data is stored in this repository.** The dataset commit is pinned and verified by blob SHA (see `configs/data_sources.yaml`).

## How the work is organised
Strict phases, each ending with a review pack that a human approves before anything is committed.

| Phase | What | Review pack |
|---|---|---|
| 0 | Contract and scaffolding | docs/phases/PHASE_00.md |
| 1 | Ingestion, provenance, inventory | PHASE_01.md |
| 2 | Quality-aware cleaning (mask, never delete) | PHASE_02.md |
| 3 | Causal features (no future information) | PHASE_03.md |
| 4 | Frozen evaluation protocol (calendar cut-offs, embargo, sealed ponds) | PHASE_04.md |
| 5 | Baselines, LightGBM, XGBoost | PHASE_05.md |
| 5b | Anchored-residual LightGBM + daily-pattern features | PHASE_05b.md |
| 6 | Forecast ranges and low-oxygen alert | PHASE_06.md |
| 7+ | SHAP, explanation checks, app, sealed final test, thesis | planned |

## Principles
- No data leakage: features use only past readings; leakage tests run on real tables.
- Honest baselines: "same as now" and "same time yesterday" are always reported.
- Success rules are written **before** running; negative results are reported.
- A sealed test (4 ponds and the last window) is used once, at the end.
- All computing runs on Modal (CPU); the laptop is for code and git only.

## Layout
`aquatic_xai/` code (data, features, splits, models, experiments, alerts, uncertainty) | `configs/` fixed settings | `modal_jobs/` one job file per phase | `tests/` unit tests | `docs/` data card, protocol, review packs, experiment reports.

## Run (example)
```
set MODAL_PROFILE=jhansimary143
python -m modal run -m modal_jobs.phase6::main --git-sha <sha>
```
Only the Modal workspace named in the project memory is used; unrelated volumes and apps are never touched.

## Not claimed
No result here is final. Final numbers will come only from the sealed test in Phase 11.
