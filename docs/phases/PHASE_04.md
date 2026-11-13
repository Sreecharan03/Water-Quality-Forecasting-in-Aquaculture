# PHASE 4 — Temporal and Unseen-Pond Evaluation Design (REVIEW PACK)

**Date:** 2026-11-13 | **Status:** Awaiting human decision (GATE 4). Not committed.

```
PHASE: 4, Temporal and unseen-pond evaluation design
OBJECTIVE: Freeze chronological windows, embargo, unseen-pond folds and the sealed test protocol before any model is trained.
DELIVERED: aquatic_xai/splits/{temporal,grouped,manifest}.py, configs/splits.yaml, modal_jobs/phase4.py, tests/test_splits.py,
           docs/evaluation_protocol.md, docs/splits/split_manifest.json (pond roles and counts only)
MODAL RUNS: ap-AVdTdTaw8OwUigoOr6iQzA (build, verify, report); later runs only re-verified and re-rendered the chart
DATASET VERSION: split sp-2dd59e32cff4 on features ft-30c94e8fe1bd (17 ponds, 72,489 origins); content hash bb7a5601...8cae
TESTS: 28 passed, 0 failed, 0 skipped (remote; 7 new split tests). Rebuild reproduced the identical assignment hash.
METRICS: N/A (no models)
COST / RESOURCES: CPU only, seconds. Billing not visible from the CLI.
SCIENTIFIC CHECK: all independence checks pass; limitations below
GITHUB: research/init at 3e82a87 (Phase 3). Phase 4 NOT committed (awaiting approval).
DECISION REQUIRED: APPROVED / REJECTED / REQUEST CHANGES
NEXT PHASE (BLOCKED): Phase 5, baselines and LightGBM/XGBoost
```

## Design in one picture
Calendar cutoffs: train to **10 Jan 2026**, validation to **20 Jan**, test after (12 h embargo at each boundary). Chart (shows validation bars and sealed ponds): `/artifacts/reports/phase4/sp-2dd59e32cff4/split_design.png`.

```
                 train (blue)         validation (green)   test
13 dev ponds    TTTTTTTTTTTTTTTTTTTTT | VVVVVVVVVV | XXXXXXXXXXX   seen-pond future test (sealed)
 4 sealed ponds ooooooooooooooooooooo | ooooooooooo | SSSSSSSSSSS   unseen-pond future test (sealed)
```
Full per-day, per-pond chart is in the Modal report `report.md`.

## What was decided and checked
| Item | Result |
|---|---|
| Cutoffs (quantiles 60% / 80% of origins, at midnight) | 2026-01-10, 2026-01-20 |
| Embargo | 12 h = 6 h lookback + 6 h horizon. Measured margins train to val and val to test print as 0.00 h at two decimals and pass the "must be >= 0" check; the embargo equals lookback + horizon exactly, with no extra padding. No observation is shared between blocks. |
| Sealed ponds (seed 20261113, 15 eligible) | `3ed4df8e`, `45e1cde5`, `b3d128ac`, `d52ddb31` |
| Dev ponds / folds | 13 ponds, 4 grouped folds of 3 ponds; `858b914c` is training-only |
| Unique (pond, origin) rows | True (72,489) |
| Sealed-pond rows in any dev role | 0 |
| Regimes checked | 11 of 11 pass: no row overlap, no pond overlap in unseen regimes, evaluation strictly in the future |

Sizes (origins with a valid 6 h DO target): train 30,996; validation 9,865; seen-pond test 9,946 (12 ponds); unseen-pond test 3,685 (4 ponds, 913 to 930 origins each); embargo 1,316 (dropped); sealed ponds' unused history 12,624.

## Why two kinds of future test
- Seen ponds, future (12 ponds): "does the model keep working on the same ponds as time passes?"
- Unseen ponds, future (4 sealed ponds): "does it work on ponds it never saw, on days it never saw?" Because every pond shares the same cutoffs, an unseen pond cannot gain from other ponds' readings from the same days.
- A diagnostic regime (unseen pond, same days) is reported only to show how optimistic the usual pond-holdout test would be. It is never used to pick models.

## Disclosures (please read)
1. **Earlier descriptive peeking.** Phases 1 to 3 computed pooled descriptive statistics over all ponds and dates, including the later-sealed ponds. No model was fitted and no rule was changed because of them. Two manual-review examples in Phase 2 (`45e1cde5`, `b3d128ac`, both 18 Jan) are from sealed ponds' unused validation period.
2. **The sealed draw is unlucky-looking but fixed.** It includes `3ed4df8e`, our messiest pond (220 conflicting duplicate timestamps, zero-value outage). I did not redraw: the seed was set before looking, and redrawing to a nicer result would be tuning on the test design. If you prefer a different rule, tell me now, before freeze.
3. **No farm identifiers** in the public data, so "unseen pond" does not mean unseen farm.
4. **Small unseen test:** 4 ponds x about 10 days (about 40 pond-day blocks). Intervals will be wide.
5. **Distribution shift:** test days are later and cooler than training. Tree models cannot extrapolate beyond the training temperature range.
6. Beyond the pooled Phase 1 to 3 statistics in point 1 and the origin counts above, I have not examined the test window, and I will not before the final run.

## Guide explanation
1. We decided in advance exactly how the models will be judged, before training any.
2. All ponds are cut at the same calendar dates: models learn from the past, tune on 10 days, and are finally tested on the last 10 days.
3. Four ponds were drawn by a fixed random number and are kept completely hidden, to test whether the model works on ponds it has never seen.
4. Gaps of 12 hours separate the blocks so that a prediction window never overlaps the next block.
5. All 11 automatic independence checks pass, and rebuilding gives identical results, so the plan is reproducible.

## Decisions I need from you
1. Approve the cutoffs (10 Jan, 20 Jan) and the 12 h embargo.
2. Approve the 4 sealed ponds exactly as drawn (or request a different rule now).
3. Approve 4 grouped folds with `858b914c` as training-only.
4. Acknowledge disclosures 1 to 5.
