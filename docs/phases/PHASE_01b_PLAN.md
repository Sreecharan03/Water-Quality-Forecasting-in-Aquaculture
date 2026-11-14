# PHASE 1b-R PLAN: replicate the method on an independent real dataset (CONTRACT, no code run yet)

**Date:** 2026-11-14 | **Status:** Contract written; awaiting your approval of the frozen rules before any code for this dataset runs.
Contract file: `configs/replication_bco.yaml`. Dataset gate result: `docs/external_data_decision.md`.

## The question
Does the method we built on the Eluru farm ponds (honest baselines, anchored LightGBM, 90% ranges, low-oxygen alert) also work on a second, independent, real dataset, tested on ponds it has not seen and on a later season?

## The data
BCO-DMO 988873: five tidal salt-marsh ponds in New Jersey, 2023-04-20 to 2024-06-03, oxygen, pH and temperature every 10 minutes, CC BY 4.0. Verified on Modal (checksum matches, 295,289 rows). **Limits to state:** salt marsh, not a managed fish pond; no feeding or aeration; temperate climate; oxygen converted from umol/kg with an approximate density.

## What changes from the Eluru work (only these)
| Item | Eluru | Here | Why |
|---|---|---|---|
| Time step | 15 min | **30 min** (take the readings at :00 and :30, no averaging or interpolation) | 10-minute data cannot reach a 15-minute grid without interpolating |
| Horizons | 15 min, 1 h, 6 h | **30 min, 1 h, 6 h** | same reason |
| "Yesterday" | 96 steps | 48 steps | same length in time |
| Pond hold-out | 4 groups | **4 folds, one pond each** (leave-one-pond-out) | only 5 ponds |
| Sealed pond | 4 ponds | **1 pond**, drawn with the fixed seed | only 5 ponds |
| Quality features | used (blind vs aware) | **blind only** | this dataset has no quality flags |

Everything else is copied: the cleaning principle (missing stays missing), the causal features with a 6 h look-back, calendar-cutoff split with a 12 h embargo, the models and their fixed settings, the metrics, the 99% blocked-bootstrap rule, the conformal ranges, the alert and its 6b decision rule. **No tuning.**

## Pass and fail rules (fixed now)
1. **Forecasts, 9 cells** (3 variables x 3 horizons), on held-out ponds: a cell passes when the model beats both simple guesses with the lower end of a 99% interval above 0. **The method replicates if at least 3 of 9 cells pass, including at least one 6 h cell.** Otherwise it does not replicate, and we say so.
2. **Ranges:** pooled coverage between 87% and 93%, with day, night and low-value coverage at least 85% (else the day/night variant).
3. **Alert (< 2.0 mg/L):** model must beat all three simple rules on average precision in each window (99% interval), calibration as Phase 6b, and the Phase 6b false-alarm rule is applied unchanged.
4. Every cell is reported, passing or not. **One round.**

## Integrity checks (must pass before any model result is read)
Features rebuilt from truncated history are identical; targets and alert labels re-derived independently; split independence checks as Phase 4; bit-identical rerun in two containers; the sealed pond and the test window never touched.

## What I expect (so we are not surprised)
- Train covers spring to autumn, validation covers winter, so **temperature will shift a lot**. Temperature cells may fail. That is a finding, not a bug.
- 25% of readings are below 2 mg/L, so the alert has a lot of events. Daily oxygen swings are smaller than at Eluru.
- With only 4 development ponds, intervals will be wide.

## Cost and time
CPU only. About 100,000 rows after subsampling, so the compute is small. About one week of work: data load and cleaning, features and split with tests, models, ranges and alert, then the review pack.

## Not in this plan
- Zero-shot transfer of the Eluru models. It needs the Eluru data on a 30-minute grid too, so it is an optional later Phase 1c with its own approval.
- Using the sealed pond or the test window.
- SHAP (Phase 7).

## Decision I need
Reply **`APPROVED PHASE 1b PLAN`** (the rules above are then frozen), or **`REQUEST CHANGES PHASE 1b PLAN: ...`**.
