# PHASE 0 — Discovery, Architecture and Secure Setup (REVIEW PACK)

**Date:** 2026-10-20 | **Status:** Awaiting human decision

```
PHASE: 0, Discovery, architecture and secure setup
OBJECTIVE: Establish what exists, what is permitted, and whether the project is feasible, before any data work.
DELIVERED: docs/research_contract.md (draft v0), this file. No code, no data, no Modal jobs.
MODAL RUNS: None. Read-only CLI queries only (environment/volume/secret/app list, config show).
DATASET VERSION: N/A (no data downloaded)
TESTS: N/A
METRICS: N/A
COST / RESOURCES: $0 spent. Estimate below.
SCIENTIFIC CHECK: See Findings.
GITHUB: Target repo is empty (git ls-remote returns no refs); nothing committed; no push attempted. Write permission NOT yet verified.
DECISION REQUIRED: APPROVED PHASE 0 / REQUEST CHANGES PHASE 0 / REJECTED PHASE 0
NEXT PHASE (BLOCKED): Phase 1, remote ingestion + data provenance
```

## Findings (verified)

### GitHub
- `Sreecharan03/Water-Quality-Forecasting-in-Aquaculture`: public, default branch `main`, size 0, **empty** (no refs). Nothing to overwrite.
- Local folder `D:\Jhansi-Aqua ML` is **not** a git repository (only the master prompt file exists).
- `git` 2.46.2 present, global identity set, credential helper `manager` (Git Credential Manager). **Push rights unverified**; first push will reveal this.
- `gh` CLI **not installed**. We can do without it. Branch protection cannot be read without auth, but an empty repo cannot have meaningful rules yet.

### Modal (profile `jhansimary143`)
- Client 1.5.3; environment `main`; authenticated token present (not displayed).
- **0 Secrets.** Existing unrelated resources: Volumes `alz-app`, `alz-raw`, `alz-processed`, `alz-runs`; app `alz-eeg` (deployed). These belong to another project and will **not** be touched. Our names will use the `aquatic-xai-` prefix.
- Quotas, credit balance and billing are not visible from the CLI; user must read them in the Modal dashboard.

### FWI data source (metadata only, nothing downloaded)
- Repo `fish-welfare-initiative/Data-Campaign-Data`, branch `main`, last push 2026-08-07.
- 17 pond CSVs `csv/ara2_*.csv`, 93–228 KB each (about 2.9 MB total), plus `Data Campaign Data.xlsx` (1.9 MB), Key_Events, QC_Flags, ProDSS files.
- README: monitors every ~15 min, Nov 2025–Jan 2026, columns Timestamp / DO mg/L / pH / Temperature °C, plus QC_Flag_DateTime / QC_Flag_DO / QC_Flag_pH.
- **Discrepancy:** README says 16 devices but 17 pond files. Consistent with a pond reinstall (e.g. `ara2_ca187575` after harvest); verify in Phase 1.
- **Zero values are equipment artifacts** (many ponds on 2026-01-08; `ara2_3ed4df8e` multi-day outage from 5 Jan; `ara2_ca187575` pH=0 after 25 Jan) and are not flagged by QC. Must be filtered explicitly and reported.
- **Licence is unclear:** README asks for citation only; no LICENSE file. Raw data must not be pushed to GitHub.
- Secondary ARA dataset page: not yet verified. Treated as out of scope until Phase 1.

### IEEE survey
- Crossref confirms DOI 10.1109/SR.2025.3595500: "Explainable AI for Water Quality Monitoring: A Systematic Review of Transparency, Interpretability, and Trust", *IEEE Sensors Reviews*, journal article, Aderemi et al. Confirmed to be a **review**, not a method.
- Independent experimental baseline paper: not yet reviewed (Phase 1/literature matrix).

## Feasibility
Dataset is small: about 90 days x 96 steps = ~8.6k rows per pond. Horizons of 1, 4 and 24 steps look plausible, but this depends on gaps. A daily seasonal baseline is feasible; **seasonal generalization is not testable** (one season). **CPU is sufficient; GPU budget proposed = $0.**

## Architecture (summary)
Core logic in `aquatic_xai/` (pure Python, testable); Modal wiring in `modal_jobs/`; UI in Streamlit on Modal; two Volumes `aquatic-xai-data` and `aquatic-xai-artifacts`; structure as in the master prompt section 4. Env split `main` only unless a dev environment is approved.

## Cost estimate (not a quote)
Ingestion + profiling of ~3 MB: seconds of CPU, effectively cents. Volumes: MBs. Tree-model experiments (Phases 5–8): modest CPU, likely single-digit dollars total. Idle UI endpoint is the main recurring risk (scale-to-zero). **Proposed ceiling for Phase 1: $2. Whole project: decided by you.** These are estimates, not measured.

## Required decisions / setup
1. Approve or revise the draft contract (targets, horizons, framing).
2. Confirm GitHub write access; choose branch strategy (`research/init` branch then PR vs direct to `main`, since repo is empty).
3. Confirm Modal workspace `jhansimary143` and the cost ceiling; check credit balance in dashboard.
4. Accept the licence risk (citation-only, no redistribution of raw data), or contact FWI.
5. Confirm 16-week schedule start date.
6. No secrets needed for the Phase 1 pilot (public GitHub source). A Modal secret will be needed later for the UI/researcher auth; names only, set through Modal's own tool.

## Risks
Small N of ponds; one season; QC flags may be derived from values; unclear licence; Modal credit/quotas unknown; GitHub push permission unverified.

## 16-week plan
Per master prompt section 15: wk 1–2 setup/data, 3–4 preprocessing/features/splits, 5–7 baselines, 8–10 XAI, 11–12 UI/serving, 13–14 final experiments, 15–16 thesis/viva. Gates may shift dates, never the leakage controls.
