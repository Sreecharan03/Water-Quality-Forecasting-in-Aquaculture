# Model card (DRAFT, validation-side evidence only)

Final numbers will come only from the sealed test (Phase 11). Nothing here is a final claim.

## What the system does
Forecasts dissolved oxygen (mg/L), pH and water temperature (°C) 15 minutes, 1 hour and 6 hours ahead for a pond, with a 90% range, plus a probability that oxygen falls below 2.0 mg/L within 1, 3 or 6 hours.

## What to use in each case (validation evidence, ponds never seen in training)
| Target | 15 min | 1 h | 6 h |
|---|---|---|---|
| Oxygen | anchored LightGBM (quality-blind) | anchored LightGBM | anchored LightGBM |
| pH | "same as now" | "same as now" | "same time yesterday" |
| Temperature | "same as now" | anchored LightGBM | anchored LightGBM |

Where a simple guess is listed, the trained model did not clearly beat it (Phase 5b). Ranges come from conformal calibration (Phase 6), using the day/night variant where the plain variant under-covered the daytime.

## Training and evaluation data
17-pond Fish Welfare Initiative continuous data (Nov 28, 2025 to Jan 30, 2026, Eluru). 13 development ponds, 4 sealed ponds. Split `sp-2dd59e32cff4`; 12 h embargo between periods.

## Intended use
Decision support for pond managers and a research demonstration. **Not** a replacement for sensors, alarms or expert judgement.

## Known limits
- One region and one season (cool months). Behaviour in other seasons or regions is unknown.
- Only 13 development ponds. Pond-to-pond differences are large; coverage varies between pond groups.
- Oxygen ranges at 6 h are wide (about ±4 mg/L).
- pH barely changes, and trained models do not beat simple guesses on pH.
- Low-oxygen alert is an **experimental risk indicator**. It ranks risk better than three simple rules (Phase 6), but after calibration (Phase 6b) its probabilities are still off at 6 h, and at the alert level chosen on other pond groups it raises false alarms on 68% of pond-days, no better than 'same window yesterday' (58%).
- Future days are cooler than training days; temperature error rises on future days.
- Sensor quality is uneven. Zeros are treated as equipment artefacts; conflicting duplicates are masked. Quality flags gave no consistent forecast benefit.
- No aerator, feeding or weather data, so causes cannot be modelled.

## Not yet done
SHAP and explanation checks (Phases 7 to 8), the sealed final test (Phase 11), the app (Phase 9), alert improvement (a second round was ruled out by the pre-registered rule).
