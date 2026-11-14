# Production-readiness plan

"Production grade" here means: **measured evidence on data the system has never seen, safe failure behaviour, and operations that can be audited and rolled back.** Each gate has a number or a yes/no test. A gate is only "met" when a report in `docs/` shows it.

## Where we stand (2026-11-14)
| Area | Status |
|---|---|
| Reproducible data and features, leakage tests, frozen split, sealed test | Done (Phases 1 to 4) |
| Honest baselines, per-cell model choice, ranges, alert | Done, validation-side (Phases 5 to 6b) |
| Evidence breadth | **Not met**: 2 months, 1 region, 13 development ponds, cool season only |
| Alert quality | **Not met** (see Phase 6b: not better than a simple rule at raising alarms) |
| Serving core: input checks, refusals, versioned bundle with hashes, train/serve parity test, rollback procedure | **Built** (Phase 10); not deployed publicly |
| CI workflow | Written; not yet seen running on GitHub |
| Live drift monitoring | **Not built**: only the training ranges and a runbook proposal exist |

## A. Evidence gates (cannot be passed by coding; need data and time)
| Gate | Pass condition |
|---|---|
| E1 More data | At least 2 seasons (include a warm or monsoon period), at least 2 farms or regions, at least 40 ponds with continuous sensors. |
| E2 Sealed test | The Phase 11 test (4 sealed ponds, last window) is run once and every pre-registered cell is reported, passing or not. |
| E3 Live shadow trial | At least 8 weeks of forecasts on live ponds, no farm action taken on them, logged and scored against what actually happened. |
| E4 Forecast accuracy | Per target and horizon: beats both simple guesses with the lower end of a 99% interval above 0 on the shadow trial. Cells that fail are served by the simple guess. |
| E5 Range validity | Coverage within 90% ± 3 points overall **and** in each pond, each day/night block and the low-oxygen stratum, on the shadow trial. |
| E6 Alert usefulness | Set with farm staff: the cost of a missed crash vs a false alarm. Pass = recall at least 90% of crashes at no more than the agreed false alarms per pond-week, and clearly fewer false alarms than the best simple rule (99% interval). Until then the alert is labelled experimental. |
| E7 Licence and ethics | Data licence resolved in writing; farm consent for any live data. |
| E8 Independent review | An external reviewer signs off the protocol and results. |

## B. Engineering gates (what we build now, all testable)
| Gate | Pass condition |
|---|---|
| B1 CI | Tests run automatically on every push (`.github/workflows/ci.yml`) and must pass before merge. |
| B2 Input validation | The service rejects or flags: missing fields, out-of-range values (for example DO < 0 or > 25 mg/L, pH outside 3 to 12, temperature outside 0 to 45 °C), stale timestamps, duplicate or out-of-order readings, flat-lined sensors. |
| B3 Abstain, never guess | If inputs are not good enough (history gap, stuck sensor, unseen range), the service returns "no forecast" with a reason, plus the simple guess when it is valid. |
| B4 Fail-safe | The service never suppresses or delays a hardware alarm. It is advisory only. Every response says which model produced it and which version. |
| B5 Versioned artefacts | Models, calibrators and the feature code are stored with a hash and the data and split versions; a response can be reproduced from its version tag. |
| B6 Drift monitoring | Per pond and per day: input distribution shift, sensor-fault rate, rolling forecast error and range coverage once truth arrives. Alert the operator when they leave pre-set bands. |
| B7 Rollback | The previous model version can be restored in one step; a model is promoted only after passing E4 to E6 on the shadow trial. |
| B8 Observability and security | Structured logs, latency and error budgets (for example p95 under 1 s per request), authentication, no raw farm data in logs or the repository. |
| B9 Disaster recovery | Artefacts and configs backed up on the Modal volume and in git; restore tested once. |
| B10 Documentation | Model card, data card, runbook (what to do when the service abstains or drift fires), known-failure list. |

## C. Order of work
1. **Now:** B1 (CI), then the serving core (B2 to B5) as a tested library plus a small API, using the models chosen so far. No clinical or farm use.
2. **Phase 7 to 8:** SHAP and explanation checks, so each forecast and alert can say why.
3. **Phase 9 to 10:** simple-name app and serving on Modal (B6 to B8).
4. **Phase 11:** sealed test, once (E2).
5. **After the thesis:** E1, E3 to E8 need new data and a partner farm. Without E1 and E3, this stays a research demonstration, and the model card must say so.

## D. What I need from you for the evidence gates
- A route to **more data**: other farms, earlier or warmer seasons, or live access.
- A **partner farm or hatchery** willing to run the 8-week shadow trial.
- Someone at the farm to say how costly a missed oxygen crash is compared with a false alarm (E6).
