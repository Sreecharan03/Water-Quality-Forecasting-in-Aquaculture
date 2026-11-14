# PHASE 6b: Alert calibration and alert level (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** APPROVED by human (GATE 6b, "push the waiting work"), committed on branch research/phase6b-external-data.

```
PHASE: 6b, calibrate the low-oxygen alert probabilities and choose the alert level on other pond groups (validation-side only)
OBJECTIVE: Fix the two Phase 6 weaknesses: untrustworthy probabilities, and false alarms no better than "same window yesterday".
DELIVERED: configs/phase6b.yaml (contract written BEFORE running), aquatic_xai/alerts/calibrate.py, modal_jobs/phase6b.py,
           tests/test_calibrate.py, docs/experiments/exp-932480b9ca47_phase6b_results.md
EXPERIMENT: exp-932480b9ca47 | reuses Phase 6 alert predictions (exp-bad07bab4b89); NO model was refitted
TESTS: 49 passed (3 new). Level chosen on other pond groups only; applied unchanged to the held-out group.
COST: a few CPU-minutes, no GPU.
GITHUB: branch research/phase6b-external-data (not merged to main).
```

## Result against the rules written before running

| Check | Result |
|---|---|
| Calibration (Brier lower AND every large reliability bin within 10 points) | **2 of 3 windows pass** (1 h, 3 h). **6 h fails**: predictions near 61% are right only 50% of the time (n=355). |
| Decision rule (6 h): model must have clearly fewer false-alarm days than "same window yesterday" at the level chosen on other pond groups, with recall within 5 points | **FAIL** |

## Numbers (unseen ponds, 6 h window, 76 episodes)
| method | episodes caught | median warning | pond-days with a false alarm |
|---|---|---|---|
| model, level chosen on other groups | 61 (80%) | 5.75 h | 68% |
| same window yesterday, level chosen the same way | 59 (78%) | 6.00 h | 58% |

Model minus baseline false-alarm share: **+9.6 points** (99% interval -2.4 to +22.4). The model is **not better**, and may be slightly worse. Giving the baseline the favourable matched-recall treatment also gives about the same (62%).

## What this means in plain words
1. Calibration helped a little (Brier 0.0323 to 0.0299 at 1 h; 0.1138 to 0.1115 at 6 h), but not enough to call the 6 h probabilities trustworthy.
2. Choosing the alert level properly did **not** make the model beat the simple rule on false alarms. All methods raise a false alarm on more than half of pond-days when they must catch 80% of episodes.
3. Why: low oxygen is extremely common here (13% of readings below 2 mg/L, an episode on most nights). A warning system must fire often, and any alert on a day-time origin with no event in the next 6 h counts as a false alarm.
4. The model's advantage from Phase 6 is real but is in **ranking** (average precision), not in a better alarm. A simple rule that reads yesterday's pattern is a strong competitor.

## Pre-registered consequence
The rule said: if this fails, the alert **stays marked experimental and there is no second round.** I am following that. I have not tried other thresholds, models or calibration methods.

## Operating point stored for the app (not an independent test)
Alert when the raw probability is at least 0.196, about **31% calibrated**. On all four groups: catches 61 of 76 episodes (80%), false alarm on 68% of pond-days. Calibrator tables are in `calibrators.json` on the Modal artifact volume (experiment folder).

## Recommendation
- Keep the alert in the app as a clearly labelled **"experimental risk indicator"** showing the calibrated probability and the plain statement "this does not beat a simple yesterday-based rule at raising alarms".
- Do not spend more rounds on the alert now. The thesis contribution here is the honest negative result and the evaluation method (episode catching, false-alarm days, other-group level selection).
- Move to **Phase 7: SHAP** for the oxygen forecast and for the alert (why does it fire?).

## Decisions I need
1. APPROVED PHASE 6b (accept this negative result and the experimental status), or REQUEST CHANGES.
2. Start Phase 7 (SHAP)?
