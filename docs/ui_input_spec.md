# UI input and output wording spec (for Phase 9)

Rule: no jargon on the main screen. Every box has a plain label, a one-line help text, and a safe default. Choices come from drop-downs of values that really exist in the data, so the student can never type something invalid.

## Forecast Lab: inputs
| # | Label the student sees | Technical meaning | Choices | Help text under the box | Default |
|---|---|---|---|---|---|
| 1 | **Which pond?** | pond ID | "Pond 1" ... "Pond 17" (the real ID in small grey text, e.g. ara2_573a2826) | Each pond is one fish pond with a sensor in the water. | first pond |
| 2 | **What do you want to know?** | target variable | Oxygen in the water (DO, mg/L) / Acidity (pH) / Water temperature (°C) | Oxygen is what fish breathe. pH tells how acidic or basic the water is. | Oxygen |
| 3 | **Pick a day** | origin date | only days with enough data (calendar greys out others) | We replay real recorded days. We do not use live sensors. | last day with data |
| 4 | **Pick a time** | origin time | only times that have enough past readings, 15-minute steps | We act as if it is this moment and ask the model what happens next. | 11:00 |
| 5 | **How far ahead?** | forecast horizon | In 15 minutes / In 1 hour / In 6 hours | Longer is harder. Short forecasts are usually more accurate. | In 1 hour |
| 6 | **Which method?** | model | Simple guess: "same as now" / Smart model A / Smart model B | The simple guess is the bar to beat. If the smart model is not better, we say so. | Smart model A |

Advanced options (hidden behind "Show more options"):
| Label | Meaning | Choices |
|---|---|---|
| Use data-quality information | quality feature group on/off | Yes / No (shows the effect on the forecast) |
| How much past should the model look at? | history window | Last 1 hour / 3 hours / 6 hours (a model experiment, not a real change to the pond) |

Examples shown next to the boxes: "Example: Pond 3, oxygen, 22 January 11:00, in 1 hour."

## Forecast Lab: outputs
| Heading | What it shows |
|---|---|
| **Our forecast** | "At 12:00 we expect oxygen of 7.4 mg/L" (value and unit). |
| **What was measured before** | Line of real past readings (solid), clearly separate from the forecast (dashed). |
| **What really happened** | The real reading at that time, if it exists, labelled *actual*. If it was missing: "Not recorded". |
| **How far off were we?** | Difference in mg/L (or pH units, °C) for the smart model and for the simple guess side by side. If the simple guess wins, the screen says so. |
| **Why did the model say this?** | Up to 5 factors with arrows (↑ raises, ↓ lowers the forecast) and a numeric size, e.g. "Oxygen 1 hour ago: ↑ 0.8 mg/L". |
| **In plain words** | One generated sentence from those numbers, e.g. "The forecast leans mostly on oxygen readings from the last hour." Never says something *caused* something. |
| **How much can we trust this explanation?** | Stability measured in our experiments (low / medium / high with the number and a link), not an invented percentage. |
| **Data label** on every number | Actual / Estimated / Missing / Unavailable, plus the source dataset and version. |

## Word list (use these everywhere)
| Do not show | Show instead |
|---|---|
| horizon | how far ahead |
| lag / lag feature | reading from X ago |
| origin time | the moment we predict from |
| SHAP value | how much this raised or lowered the forecast |
| baseline / persistence | simple guess: "same as now" |
| MAE | average miss (in mg/L, pH, °C) |
| unseen pond | a pond the model never saw |
| leakage | using information from the future (we prevent this) |
| quality flag | the sensor warned this reading may be unreliable |

## Do-not rules
- No "good / bad / safe / dangerous" colouring unless a cited source defines the range. The only thresholds shown are FWI's own flag rules, labelled with their source.
- No percentage "accuracy" gauge.
- If the chosen pond/time has a gap or no valid history, show "Unavailable: not enough recent readings" and never a made-up number.
- Every screen has a short "What am I looking at?" note.

## Other pages: inputs
- **Explore Real Data:** Which pond? / Which parameter? / From date / To date / Show: Original readings | Cleaned readings | Both.
- **Compare Models:** What do you want to know? / How far ahead? / Which test? (Practice period / Tuning period / Final test, with the final test shown only after the sealed run) / Ponds: Ones the model saw | Ponds it never saw.
- **Explanation Reliability, Data Lineage, Viva Mode:** read-only; the only input is a page or section selector.
