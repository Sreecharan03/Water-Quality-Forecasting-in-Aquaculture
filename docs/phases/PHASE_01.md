# PHASE 1 — Remote Data Provenance and Feasibility (REVIEW PACK)

**Date:** 2026-10-20 | **Status:** Awaiting human decision (GATE 1). Not committed.

```
PHASE: 1, Remote data provenance and feasibility
OBJECTIVE: Ingest the FWI source directly into Modal, record provenance, and produce an honest inventory and feasibility table.
DELIVERED: aquatic_xai/data/{ingest,profile}.py, modal_jobs/{common,phase1}.py, configs/data_sources.yaml, tests/test_profile.py, docs/data_card.md
MODAL RUNS: ap-WsR1xtMo6ZZp1pSxk4Awt9 (ingest + profile; its first test run had 1 failure from a wrong expected value in MY test, fixed)
            ap-RpMfN8Y7lNJSURWZZablub (4/4 tests pass; diagnostics)
DATASET VERSION: commit 4cfa138e725db541e7ae14b89170909bef7dafb1; 17 ponds; 72,750 rows; 23 files / 2,983,335 bytes
TESTS: 4 passed, 0 failed, 0 skipped (remote). Blob-SHA integrity verified on all 23 downloaded files.
METRICS: N/A (no models)
COST / RESOURCES: CPU only, image build 8 s, jobs run for seconds. Billing is not visible from the CLI; expected well under $0.10. Please confirm in the Modal dashboard.
SCIENTIFIC CHECK: No cleaning, imputation or deletion was performed. Findings listed in data_card.md.
GITHUB: Branch research/init at a5a71d2 (Phase 0). Phase 1 files NOT committed (awaiting approval).
RISKS: see below
DECISION REQUIRED: APPROVED / REJECTED / REQUEST CHANGES
NEXT PHASE (BLOCKED): Phase 2, quality-aware preprocessing
```

## Feasibility table (usable origins = lookback fully valid, target valid at t+h; all 17 ponds)
Computed on the 15-min grid; invalid = null or zero; no values were invented.

| Horizon | Lookback 1 h (L4) | Lookback 6 h (L24) | Per-pond range (L24) | Verdict |
|---|---|---|---|---|
| 15 min (h1) | 65,932 | 45,279 | 1,105 – 4,125 | **GO** |
| 1 h (h4) | 65,431 | 44,991 | 1,062 – 4,112 | **GO** |
| 6 h (h24) | 64,172 | 44,161 | 1,039 – 4,048 | **GO (provisional)** |

Figures are for the DO target, summed over the 17 ponds from the per-pond report table. Per-target (pH, Temp) counts are in `inventory.json` and were not summed here.

Provisional targets: DO, pH, Temperature, all three are present and valid for each horizon. Only about 7 weeks of data means the chronological test block per pond will be roughly 1,000 rows, and CIs will be wide.

## Items needing your decision at Gate 1
1. **Dataset choice:** use the FWI Data Campaign only (recommended). The secondary ARA historical release is NOT verified; leave out of scope unless you want a separate review.
2. **Conflicting duplicates** (ponds `3ed4df8e`, `6ca69422`): choose between excluding those timestamps, excluding those ponds from the primary analysis, or investigating with FWI. I recommend excluding the conflicting timestamps and reporting a sensitivity analysis.
3. **Zeros:** treat as missing (FWI says they are artifacts). I recommend this for Phase 2, while keeping the original rows in the raw volume.
4. **Calibration break on 8–9 Jan:** treat as a documented event; evaluate whether it shifts sensor behaviour before pooling across it. Possible use as a natural out-of-time split boundary.
5. **Licence:** continue with citation-only terms, no raw redistribution. Optionally email FWI for explicit permission.
6. **The 4 ProDSS-only ponds** are excluded (no continuous series). Confirm.
7. **README says 16 devices, Key_Events lists 17 continuous devices and 17 CSVs exist.** Treat 17 as correct (FWI documentation is internally inconsistent by one).

## Risks
Short record (7–9 weeks) and single season; many gaps (3,010 gaps >20 min); sensor calibration and harvest events inside the window; arbitrary duplicate resolution; QC flags partly computed from values; unclear licence. No hypothesis can be tested without Phase 2 decisions.

## Guide explanation
1. We downloaded the real pond sensor files straight into the cloud and checksummed every one.
2. Each pond records oxygen, acidity and temperature every 15 minutes for roughly 7 weeks.
3. The files contain real problems: zero readings from machine resets, two ponds with conflicting duplicate entries, and a few long outages.
4. We counted every problem but removed nothing yet, so every later cleaning choice can be justified.
5. There are enough clean stretches to forecast 15 minutes, 1 hour and 6 hours ahead, with the caveat that the data covers only one short winter period.
