# Chapter 7: The application (draft)

## 7.1 Purpose and users
A pond owner pastes or uploads their own readings (time, oxygen, pH, temperature; at least 25 hours) and receives forecasts for 15 minutes, 1 hour and 6 hours, each with a "likely between" range, a "how did we get this?" explanation, and an experimental "chance of very low oxygen". The language is deliberately plain: inputs are named keys with examples, and no jargon appears on screen.

## 7.2 Architecture
- **Front end:** plain HTML, CSS and JavaScript (no libraries). Text is inserted as text only; a content-security policy blocks outside scripts and styles.
- **Backend:** FastAPI. Endpoints: forecast, example (made-up data), template, about, health. Readings are processed in memory and not stored or logged.
- **Library:** `aquatic_xai.serving`: input checks and grid placement (reusing the research code), prediction engine, plain-language layer, model bundle.
- **Model bundle:** LightGBM boosters and a manifest with data and split versions, the training range, ranges, calibrators, and a SHA-256 for every file. `final_v1` is the exact artefact tested in Phase 11; `final_v2` replaces the two failed 6-hour model cells with "same time yesterday".

## 7.3 Safety by refusal
The app does not guess when: there are fewer than 25 hours; oxygen or pH has been exactly constant for 2 hours (stuck sensor); less than half of the last 24 hours is available; the latest reading is missing; or a reading lies far outside what the models learned from (more than 10% beyond the training range). Readings at the edge of that range get a warning. Exact zeros, impossible values, non-numbers and conflicting duplicates are ignored and reported. A test shows that a pond with temperatures 15 °C lower than the training range gets no temperature forecast while oxygen is still forecast. This directly answers the salt-marsh finding that models do not transfer across very different environments.

## 7.4 Honest wording
Where the model did not beat a plain guess, the card says "We simply repeated the latest reading" or "We used the reading from the same time yesterday", with the reason. Where the explanation test failed (oxygen at 15 minutes), a warning appears. The alert is badged *Experimental*; a banner states that the system is a research demonstration and not a safety device.

## 7.5 Verification
- 74 tests pass, including API behaviour, input handling, refusals and security headers.
- **Train/serve parity:** for 19 moments from four development ponds, forecasts, ranges and alert probabilities from the app equal those of the research pipeline exactly. **A real skew was found first**: floating-point noise of about 1e-12 in rolling statistics, which depends on how much history is supplied, had made trees split on noise, shifting predictions by up to 0.016. The fix was to round model inputs to 8 decimals in both training and serving; the bundle was rebuilt and re-verified.
- Speed: median 0.10 s per forecast.

## 7.6 What the app is not
Not a safety device; not deployed publicly; not tested on live traffic; no monitoring job yet (the runbook proposes thresholds); previewed only with made-up data; and covered by the limits in Chapter 8.
