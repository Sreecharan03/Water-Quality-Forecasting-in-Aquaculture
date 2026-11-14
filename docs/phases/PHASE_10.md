# PHASE 10: Serving core and checks (REVIEW PACK)

**Date:** 2026-11-14 | **Status:** Committed under the standing instruction "complete all the phases" (change requests welcome). **Not deployed publicly.**

```
PHASE: 10, FastAPI service with input checks, honest "no forecast" answers, ranges, risk, reasons, versioned model bundle, and tests
DELIVERED: app/main.py; aquatic_xai/serving/{ingest,engine,bundle,plain}.py; modal_jobs/{phase10,serve}.py; tests/test_serving.py (+14);
           requirements-app.txt; docs/app_runbook.md
BUNDLE: models/final_v1 on the Modal artifact volume; trained on the DEVELOPMENT ponds, training and validation windows only
        (sealed ponds and test windows never read); 3 seeds per model; SHA-256 of every file in the manifest
TESTS: 74 passed on Modal (14 new for the service)
VERIFY (modal run -m modal_jobs.phase10::verify): all_pass = true
```

## What the service does
| Step | Behaviour |
|---|---|
| Read | Pasted text or uploaded file; separators and column names are recognised (oxygen / DO, temperature / temp, ...). |
| Clean (same rules as the research pipeline) | exact zeros ignored; impossible values ignored; text in number columns ignored; conflicting duplicate times ignored; readings placed on a 15-minute grid within 3 minutes; **nothing is ever filled in**. |
| Refuse in plain words | fewer than 25 hours; sensor stuck for 2 hours; less than half of the last 24 h available; latest reading missing; reading **far outside the training range** (more than 10% beyond the training minimum and maximum). Other variables still get forecasts. |
| Warn | reading beyond the 1st to 99th percentile of the training data; day/month/year date assumption; ignored readings. |
| Forecast | per target and distance, the method chosen by the pre-registered rules: trained model (oxygen 15 min, 1 h, 6 h; temperature 1 h, 6 h) or plain guess (pH at all distances; temperature 15 min). |
| Range | conformal "likely between", calibrated on ponds the model never saw; day/night version where the plain version under-covered. |
| Low-oxygen chance | three windows, calibrated; High chance means at or above the 31% level chosen in Phase 6b (6 h) or 50% (1 h and 3 h, generic, not tested); marked experimental. |
| Reasons | top three, merged and worded in everyday sentences; a warning when the Phase 8 stability test failed. |

## Results of the checks
- **Bundle integrity:** every file hash matches its manifest.
- **Train/serve parity:** for 19 moments from 4 development ponds, the app (fed only raw readings, through the HTTP API) gives **exactly** the same forecasts, ranges and alert probabilities as the research pipeline (max difference 0.0).
- **Out-of-range guard:** a pond with temperatures 15 °C colder than anything the models learned gets **no temperature forecast** and a plain explanation, while oxygen is still forecast.
- **Speed:** p50 0.10 s, p95 0.10 s per forecast (target under 1 s).
- **Safety headers:** content-security-policy that blocks outside scripts and styles, no sniffing, no referrer, no caching of API answers; request size limits.

## A real problem found and fixed (train/serve skew)
The first parity test **failed**: forecasts differed by up to 0.016 and alert probabilities by 0.005. Cause: rolling statistics carry about 1e-12 of floating-point noise that depends on how much history is fed in, and the trained trees had split on that noise. Fix: model inputs are rounded to 8 decimals, both when training the bundle and when serving. The bundle was rebuilt (it was not yet used by anything), and the parity test then passed with an exact match. The earlier research results (Phases 5 to 8) are unaffected: they used the offline pipeline throughout, and the noise only affects individual predictions at the 0.001 to 0.016 level.

## Known limits
- Ranges for the final bundle were calibrated on the validation errors of the earlier (non-final) models, which is an approximation.
- The 1 h and 3 h "High chance" level (50%) is generic and was not tested.
- Day/night uses local clock hours as typed by the owner; no time-zone handling.
- No live monitoring job has run yet (the runbook proposes thresholds).
- The app has been previewed with made-up example data only.

## Not done on purpose
- **Not deployed publicly.** `modal_jobs/serve.py` exists, but deploying gives anyone with the link access. Needs your explicit decision.
- The sealed final test (Phase 11).

## Decisions I need
1. Accept Phases 9 and 10 (wording, behaviour, refusal rules), or request changes.
2. Say whether you want a temporary link (`modal serve`) for a demonstration to your guide.
3. **Phase 11 (sealed final test, run once): confirm before I run it.**
