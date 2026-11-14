# PHASE 1b-R: method replication on BCO-DMO salt-marsh ponds (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** APPROVED by human (GATE 1b-R, "complete all the phases"), committed on branch research/phase6b-external-data.

```
PHASE: 1b-R, replicate the frozen method on an independent real dataset (validation-side only)
OBJECTIVE: Does the Eluru-built method (baselines, anchored LightGBM, 90% ranges, low-oxygen alert) work on a second real dataset?
DELIVERED: aquatic_xai/data/external.py, generalised grid code (day length, step, long horizon), modal_jobs/replication_bco.py,
           tests/test_external.py, docs/experiments/exp-20f6d2ca9f07_replication_bco.md; contract configs/replication_bco.yaml (frozen before any code ran)
DATA: BCO-DMO 988873 (md5 verified), 5 ponds, 30-minute subsample, 98,429 rows; features bco-10b684a9730d, split bsp-50f01c356bb7
SPLIT: train to 2023-12-22, validation to 2024-03-13, test after; 12 h embargo; sealed pond = Shark (drawn with the fixed seed); 4 held-out folds, one pond each
INTEGRITY (all passed BEFORE any model result was read): 200 feature prefix checks 0 mismatches (max diff 0.0); 200 daily-feature checks 0; 1,800 target re-derivations 0;
           600 alert-label checks 0; 600 yesterday-window checks 0; identity check max 14%; all 11 split regimes pass (gap 0.5 h >= 0); same task in two containers: max difference 0.0
TESTS: 55 passed (6 new). Eluru code paths unchanged by default (day 96, step 15 min, long horizon 24).
EXPERIMENT: exp-20f6d2ca9f07 | 45 forecast tasks + 15 alert tasks | 375 container-seconds, CPU only
GITHUB: branch research/phase6b-external-data (not merged to main).
```

## Result against the pre-registered rules (held-out ponds, validation window, 99% intervals)
| Rule | Result |
|---|---|
| Forecasts: at least 3 of 9 cells beat both simple guesses, including a 6 h cell | **3 of 9 pass, including a 6 h cell: "method replicates" = YES** (by the rule as written) |
| Range coverage | 7 of 9 cells pass (6 h oxygen and 6 h pH fail the low-value check) |
| Alert beats 3 baselines | **0 of 3 windows** |
| Alert calibration | 1 of 3 windows (6 h) |
| Alert false-alarm decision rule | **FAIL** (model minus baseline: -1.1 points, 99% interval -10.1 to +7.6) |

## What the "YES" really means (please read)
The rule I froze was lenient on purpose, and it is met, but **the cells that pass are different from Eluru's**:
| | Eluru (Phase 5b) | Salt marsh (this phase) |
|---|---|---|
| Oxygen | beats both simple guesses at 15 min, 1 h, 6 h | **fails everywhere**: worse than "same as now" at 30 min and 1 h; at 6 h, beats "same as now" (+28%) but ties "same time yesterday" (-5.6%, interval -13.0 to +0.8) |
| pH | fails | fails (worse than "same as now" at 30 min and 1 h; 6 h ties "yesterday") |
| Temperature | passes at 1 h and 6 h, fails at 15 min | **passes at all three** (+52%, +53%, +40% over "same as now") |
So the claim "the anchored model helps for oxygen" does **not** replicate. The claim "it helps for temperature" does, more strongly. The only result that holds in both datasets: **at 6 h, the anchored model clearly beats "same as now" for oxygen, pH (+32%) and temperature, and "same time yesterday" is a strong competitor for oxygen and pH.**

## Other findings
1. **The validation window is winter, so low oxygen is rare there** (event rates 2.1%, 3.3%, 5.0% against about 25% over the whole year). Only 36 episodes occur in the held-out ponds. The alert test is therefore **underpowered, not clearly negative**: all nine point estimates favour the model over the baselines, but only three comparisons (against "same window yesterday" at 1 h and 3 h, and against trend at 6 h) are clear at 99%. A fair alert test needs a validation window that includes summer.
2. **Ranges:** pooled coverage is 90% in all nine cells, but in the low-value stratum 6 h oxygen covers only 62% and 6 h pH 74%. Per-pond coverage in the oxygen cells ranges from 76% to 96%. Averages hide pond differences.
3. **Calibration:** isotonic calibration did not make the 1 h and 3 h probabilities trustworthy; the 6 h window passes.
4. **Near-zero oxygen is frequent** (12% to 18% of valid readings at or below 0.05 mg/L). They were kept as valid per the contract. It may be real night anoxia in shallow marsh ponds or a sensor floor. We cannot tell from the data alone.
5. **Calendar design effect:** train = spring to autumn, validation = winter. This is a hard test of seasonal extrapolation, which is exactly what we lack at Eluru.

## Honest conclusion
- The **evaluation method** (leakage-checked features, calendar split with embargo, held-out ponds, blocked-bootstrap intervals, pre-registered rules) transfers cleanly and produced a decisive, auditable result on a second dataset.
- The **modelling results do not transfer uniformly**: oxygen gains seen at Eluru are absent here; temperature gains are larger. We should not claim a universal oxygen forecaster.
- Simple guesses remain hard to beat for oxygen and pH. This agrees with the 2025 aquaponic-pond paper in the literature matrix (to be checked in full text).

## Limits (state in the thesis)
Tidal salt marsh, not managed aquaculture; 30-minute subsample of 10-minute data; oxygen unit conversion is approximate; only four held-out ponds; one winter validation window; the sealed pond (Shark) and the test window remain unused.

## Recommendation
1. Accept the result as is, including "method replicates: YES (weak)" and the failed alert rules.
2. Do **not** retune anything on this dataset.
3. For a fair alert test, a later, separately approved Phase 1b-R2 could use the sealed test window (spring) only once, at the end, together with the Eluru sealed test (Phase 11).
4. Move on to **Phase 7 (SHAP)**. The finding that different variables help in different datasets is itself something explanations can examine (for example, which inputs drive the temperature gain).
5. Still pending: the Fish Welfare Initiative data request (aquaculture ponds, more seasons).

## Decisions I need
1. APPROVED PHASE 1b-R (accept these results, including the weak replication and failed alert rules), or REQUEST CHANGES.
2. Start Phase 7 (SHAP) next?
