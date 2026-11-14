# Chapter 6: Explanations and their validation (draft)

## 6.1 What was explained
Eleven cells where a model helped: Eluru oxygen at 15 minutes, 1 hour and 6 hours; Eluru temperature at 1 hour and 6 hours; Eluru low-oxygen alert for the next 1, 3 and 6 hours; salt-marsh temperature at 30 minutes, 1 hour and 6 hours. Cells where a plain guess was used were not explained, because there is no model to explain.

## 6.2 What the models use (mean absolute SHAP, validation window)
- **Short range (15 minutes, 1 hour):** the latest readings and the **time of day** dominate. The oxygen alert for the next hour is led by oxygen right now (mean absolute SHAP 1.63 log-odds).
- **6 hours ahead:** the pond's own **daily pattern** takes over. For oxygen, the top inputs are how far yesterday's value is from now, time of day, and yesterday's value at the target time; the daily-pattern family carries 39% of the attribution (oxygen) and 38% (Eluru temperature; 31% in the salt marsh).
- **Alert for the next 6 hours:** led by the lowest oxygen in the same window yesterday (1.00), then oxygen now, time of day and the lowest oxygen of the last 24 hours. In words: ponds that crashed at this time yesterday tend to crash again tonight.
- **Temperature:** time of day and yesterday's temperature dominate; the salt marsh leans more on the 3-hour trend.

## 6.3 Pre-registered expectations
X1 (daily-pattern family at least 25% at 6 hours for oxygen and temperature): **met in all 3 cells.** X2 (history family at least 50% at the shortest distance): **not met** (42%, 41%, 15%). X3 (time of day among the top three families for temperature): met in 3 of 5 cells.

## 6.4 Are the explanations trustworthy? (E1 to E4)
**9 of 11 validated.** The two that failed: Eluru oxygen at 15 minutes (the main model passes faithfulness but only 2 of 4 pond-group models do) and salt-marsh temperature at 30 minutes (rank correlation across seeds 0.84, below 0.90). All three alert explanations passed all four tests. Stability is highest where the model beats the baselines by a wide margin.

## 6.5 What the explanations do and do not show
- They describe **what the model uses**, not what causes oxygen to fall.
- Correlated inputs share attribution, so family shares are more reliable than single-input ranks.
- A feature like 24-hour mean temperature may stand in for pond identity or season; stability across pond groups reduces but does not remove this concern.
- Faithfulness used median replacement, which can create unusual inputs.
- Four held-out groups of one to four ponds make the pond-stability test coarse.

## 6.6 An example, in plain words
For a 6-hour low-oxygen warning, the app can say: "The lowest oxygen in the same hours yesterday raises the chance. Oxygen right now lowers it. The time of day raises it." (These sentences are generated from the top SHAP contributions and merge sine and cosine of the hour into "the time of day".)
