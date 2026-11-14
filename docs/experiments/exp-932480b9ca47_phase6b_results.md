# Phase 6b results, experiment `exp-932480b9ca47`

- Reuses the Phase 6 alert predictions (`exp-bad07bab4b89`); no model was refitted. Split `sp-2dd59e32cff4` unchanged. Validation-side only; sealed test not used.
- Code commit `4f1d539-unco`. Contract: `configs/phase6b.yaml`, written before running. One round.

## A. Are the probabilities now trustworthy? (unseen ponds; isotonic fitted on the other three pond groups)

| window | Brier raw | Brier calibrated | bins (calibrated prediction -> actual rate, n) | criterion |
|---|---|---|---|---|
| 1h | 0.0323 | 0.0299 | 2% -> 2% (8158); 18% -> 15% (326); 44% -> 59% (96); 59% -> 55% (259); 86% -> 88% (137); 98% -> 98% (1273) | PASS |
| 3h | 0.0654 | 0.0631 | 4% -> 4% (6797); 17% -> 16% (1149); 40% -> 46% (209); 56% -> 48% (275); 81% -> 82% (470); 99% -> 98% (1318) | PASS |
| 6h | 0.1138 | 0.1115 | 5% -> 6% (3710); 17% -> 17% (2951); 40% -> 45% (992); 61% -> 50% (355); 79% -> 77% (924); 100% -> 97% (1297) | fail |

**2 of 3 windows pass** (pooled unseen Brier score of the calibrated probabilities is lower than the raw one in every window, and every reliability bin with n >= 100 has |predicted - observed| <= 10 points). Calibration changes the displayed probability only; it does not change the ranking of risk (average precision is unchanged up to ties).

## B. Alert level chosen on other pond groups (6 h window), then applied to the held-out pond group

Rule: the strictest alert level that catches at least 80% of episodes on the other three pond groups. The baseline 'same window yesterday' gets its level chosen the same way.

| held-out group | model level (raw / calibrated) | model recall | model false-alarm days | baseline level | baseline recall | baseline false-alarm days |
|---|---|---|---|---|---|---|
| fold 0 | 0.201 / 30% | 17/22 (77%) | 15/30 | -2.530 | 20/22 (91%) | 15/30 |
| fold 1 | 0.207 / 35% | 13/16 (81%) | 19/31 | -2.450 | 13/16 (81%) | 17/31 |
| fold 2 | 0.176 / 35% | 14/17 (82%) | 28/32 | -2.310 | 12/17 (71%) | 20/32 |
| fold 3 | 0.204 / 29% | 17/21 (81%) | 23/32 | -2.250 | 14/21 (67%) | 21/32 |

### Pooled over the 4 held-out pond groups (the pre-registered test)

| method | episodes | caught | recall | median warning (h) | share of pond-days with a false alarm |
|---|---|---|---|---|---|
| model | 76 | 61 | 80% | 5.75 | 68% |
| same window yesterday | 76 | 59 | 78% | 6.00 | 58% |

Difference in false-alarm share (model minus baseline): **+9.6 points** (99% interval -2.4 to +22.4; blocks = pond-days, n=125). Recall difference (model minus baseline): +3 points.

**Pre-registered verdict: FAIL** (pooled over the 4 held-out pond groups: (false-alarm pond-day share of model) minus (that of the baseline) has a 99% blocked-bootstrap upper bound < 0, AND model episode recall >= baseline episode recall - 0.05).

### Secondary (favours the baseline): baseline given the strictest level that matches the model's realised recall on the same held-out data

- Baseline recall 80%, false-alarm pond-days 77/125 (62%), median warning 6.00 h.

## C. Operating point for the app (chosen on all four pond groups, so it is NOT an independent test)

- Alert when the model's raw probability is at least **0.196**, which is a calibrated probability of about **31%**. On these groups it catches 61/76 episodes (80%), with a false alarm on 68% of pond-days.
- Calibrator lookup tables are stored in `calibrators.json` in the experiment folder (for the app and Phase 9).