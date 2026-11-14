# Model card (bundle `final_v2`; includes the sealed final test of `final_v1`)

The sealed final test (Phase 11) was run once on 4 never-seen ponds over about 10 late-January days. Its full results are in `docs/experiments/final_test_report.md`; the summary is below.

## What the system does
Forecasts dissolved oxygen (mg/L), pH and water temperature (°C) 15 minutes, 1 hour and 6 hours ahead for a pond, with a 90% range, plus a probability that oxygen falls below 2.0 mg/L within 1, 3 or 6 hours.

## What to use in each case, and what the final test showed (never-seen ponds)
| Target | 15 min | 1 h | 6 h |
|---|---|---|---|
| Oxygen | trained model: **missed by 0.33 mg/L, plain guess 0.39 (passes)** | trained model: **0.71 vs 1.12 (passes)** | "same time yesterday" (model 1.66 was not clearly better than yesterday's 1.52, failed) |
| pH | "same as now" | "same as now" | "same time yesterday" |
| Temperature | "same as now" | trained model: **0.10 vs 0.14 °C (passes)** | "same time yesterday" (model 0.25 was worse than yesterday's 0.20, failed) |

The two 6-hour cells were switched to the plain guess in `final_v2` after the test, using the pre-registered fallback rule; that switch has not itself been re-tested. Ranges are conformal and never under-covered in the final test (91.8% to 99.2%) but were usually wider than needed.

## Training and evaluation data
17-pond Fish Welfare Initiative continuous data (Nov 28, 2025 to Jan 30, 2026, Eluru). 13 development ponds, 4 sealed ponds. Split `sp-2dd59e32cff4`; 12 h embargo between periods.

## Intended use
Decision support for pond managers and a research demonstration. **Not** a replacement for sensors, alarms or expert judgement.

## Known limits
- One region and one season (cool months). Behaviour in other seasons or regions is unknown.
- Only 13 development ponds. Pond-to-pond differences are large; coverage varies between pond groups.
- Oxygen ranges at 6 h are wide (about ±4 mg/L).
- pH barely changes, and trained models do not beat simple guesses on pH.
- Low-oxygen alert is an **experimental risk indicator**. In the final test its ranking beat three simple rules for the next 3 and 6 hours, but its percentages were too high (0 of 3 windows calibrated) and it raised a false alarm on 98% of pond-days at the 'High chance' level. Validation-time notes follow: It ranks risk better than three simple rules (Phase 6), but after calibration (Phase 6b) its probabilities are still off at 6 h, and at the alert level chosen on other pond groups it raises false alarms on 68% of pond-days, no better than 'same window yesterday' (58%).
- Future days are cooler than training days; temperature error rises on future days.
- Sensor quality is uneven. Zeros are treated as equipment artefacts; conflicting duplicates are masked. Quality flags gave no consistent forecast benefit.
- No aerator, feeding or weather data, so causes cannot be modelled.

## Not yet done
Re-testing `final_v2` on fresh data; any other region, season or longer period; a live shadow trial; alert improvement (a second round was ruled out by the pre-registered rule).
