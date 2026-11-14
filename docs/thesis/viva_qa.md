# Viva questions and honest answers (draft)

Learn the reasoning, not the wording. Every number is in the reports named in brackets.

## About the project
**1. What is your project in one sentence?** A forecasting system for pond oxygen, pH and temperature that is tested honestly on ponds it never saw, gives a range with each forecast, explains itself, and refuses to guess when its inputs look wrong.

**2. Why is this problem important?** Low oxygen can kill fish. In our ponds 13% of readings were below 2 mg/L, so early warning matters.

**3. What is your main contribution?** Not a record-breaking accuracy. It is an auditable evaluation protocol and an honest account of where machine learning helps and where a simple guess does just as well. (Ch 1, 5.)

**4. Is anything in your work new?** I do not claim novelty until the literature search is finished and verified. What I can say is what we built and measured. (Ch 2 warning.)

## About data and leakage
**5. What is data leakage and how did you prevent it?** Using information from the future or from the test set. Features use only readings up to the origin; two tests on the real tables confirmed it (truncating the future changes nothing; targets re-derived independently). The split uses fixed calendar dates with a 12-hour embargo; four ponds were sealed; the sealed test was run once. (Ch 3.)

**6. Why a 12-hour embargo?** Features look back 6 hours and targets look ahead 6 hours; 12 hours ensures no training target window touches a test feature window.

**7. Why not a random split?** Neighbouring 15-minute readings are almost identical, so a random split would test on near-copies of training rows and look far better than reality.

**8. What are the limits of the data?** One region, about nine weeks of a cool season, 17 ponds, unclear licence, no farm IDs, no aerator or feeding data. (Ch 8.)

**9. What did you do about zeros and bad readings?** Exact zeros are treated as sensor faults (the provider documents this), impossible values and conflicting duplicates are masked, nothing is filled in. In the salt-marsh data about 12% to 18% of oxygen values were near zero; I kept them and said so.

## About models and results
**10. What are your baselines and why do they matter?** "Same as now" and "same time yesterday". Without them a model can look good while adding nothing. At 6 hours "yesterday" was as good or better than the model in the sealed test.

**11. Which results are strongest?** Oxygen at 15 minutes and 1 hour and temperature at 1 hour beat both baselines clearly in the sealed test on four never-seen ponds (Phase 11).

**12. Which results failed?** Oxygen and temperature at 6 hours in the sealed test; data-quality features (H1); the low-oxygen alert as an alarm; calibration of the alert percentages. All are reported.

**13. Why did you use LightGBM and not deep learning?** The data are small tabular series; trees are strong and explainable with exact SHAP. A neural model would add cost without fixing the real weaknesses (missing daily pattern, predicting levels instead of changes). It is listed as future work under the same protocol.

**14. What is the anchored residual model?** The forecast is a starting guess (same as now, or same time yesterday) plus a learned correction. It fixed two problems: models rebuilding the level from scratch, and missing the daily pattern.

**15. Did you tune hyperparameters?** No. Fixed settings, to avoid overfitting a small dataset and to keep the comparison fair.

**16. How do you know the results are not luck?** Intervals use a blocked bootstrap (blocks of pond by day), 99% for headline rules; results are reproduced bit-for-bit across containers; seed spread was about 1% of the error; and the final test was run once.

**17. Your final test had only four ponds and ten days. Is that enough?** It is small, which is why I describe it as evidence for the method, not a guarantee. The intervals show the uncertainty.

**18. Why did the 6-hour models fail the final test when they passed validation?** In validation "yesterday" was already close; in the final test it was as good or better. Possible reasons: a calmer period and different ponds. I did not retune; I applied the pre-registered fallback to the plain guess and stated that this switch is not itself re-tested.

## About ranges and the alert
**19. What is a conformal range?** A range around the forecast sized from errors on other ponds, so it contains the truth about 9 times in 10. In the final test coverage was 91.8% to 99.2%: valid but usually wider than needed.

**20. Why is your alert not usable as an alarm?** Low oxygen is common in these ponds, so any alarm that catches most episodes fires on most days (98% of pond-days at the tested level, against 75% for the simple rule). It ranks risk well, but its percentages were also too high.

**21. Why the 2 mg/L threshold?** A widely used severe-low level, and 3 mg/L would fire on 21% of readings. It was fixed from descriptive counts before any model was trained.

## About explainability
**22. What is SHAP?** A way to say how much each input pushed a prediction up or down. For trees, LightGBM gives the exact values.

**23. How do you know your explanations are trustworthy?** Four pre-registered tests: same across seeds, across held-out pond groups, across time halves, and faithful (removing the inputs SHAP calls important must hurt more than removing random ones). 9 of 11 passed; the two that failed are flagged. (Ch 6.)

**24. Do the explanations show what causes low oxygen?** No. They show what the model uses. For example "lowest oxygen in the same hours yesterday" is a strong signal, but the cause is the pond's daily cycle, which I did not model physically.

## About the second dataset and the app
**25. Why a second dataset and what did it show?** To test whether the method transfers. Salt-marsh ponds are very different. The method transferred weakly: temperature improved, oxygen did not. So I do not claim a universal oxygen forecaster. I also found two other datasets were synthetic and rejected them.

**26. What does your app do when it is not sure?** It refuses: too little history, stuck sensor, too many gaps, or readings far outside the training range. Other variables are still forecast.

**27. What was the train/serve skew you found?** Floating-point noise of about 1e-12 in rolling statistics, depending on history length, which trees had split on. It changed predictions by up to 0.016. Rounding inputs to 8 decimals in training and serving fixed it, and the app now matches the research pipeline exactly.

**28. Is the app safe to use on a real farm?** Not as the only safeguard. It is a research demonstration, tested on one region and season, not deployed, not tested live. It must not replace sensors and alarms.

## Hard questions
**29. If simple guesses are so strong, what is the point of machine learning here?** The point is to know. The gains at short range are real but modest, and we can state where they stop. The system uses the model only where it clearly beat the guesses.

**30. What would you do with more time?** More seasons and farms, aerator and weather records, a live shadow trial, a calibrated alert checked on a summer window, and compare a Temporal Fusion Transformer under the same rules.
