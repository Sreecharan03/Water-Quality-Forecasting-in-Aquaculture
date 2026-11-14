# Chapter 1: Introduction (draft)

## 1.1 The problem
Dissolved oxygen in a fish pond follows a daily cycle: it rises with daylight photosynthesis and falls at night. If it drops too low, fish are stressed or die. A farmer who could see a low-oxygen night coming a few hours early could aerate in time. In our data, 13% of oxygen readings in the development ponds were below 2 mg/L, so the risk is not rare.

## 1.2 Why existing forecasting claims are hard to trust
Three habits make forecasting results look better than they are: (1) testing on days or ponds the model has effectively seen (leakage); (2) not comparing against trivial guesses such as "the same as now"; (3) reporting only the best result after many tries. A model that "predicts oxygen with 95% accuracy" may add nothing over repeating the last reading.

## 1.3 Research questions
- **RQ1.** Do trained models beat honest simple baselines at 15 minutes, 1 hour and 6 hours ahead, on ponds they never saw and on later days?
- **RQ2.** Does data-quality information (sensor flags, missing-data counts) improve forecasts? (Hypothesis H1.)
- **RQ3.** Can each forecast carry an honest range that holds on unseen ponds?
- **RQ4.** Can a low-oxygen early-warning probability beat simple rules, and is it usable as an alarm?
- **RQ5.** Are SHAP explanations of the models stable and faithful, and which can be trusted?
- **RQ6.** Does the method work on a second, independent real dataset?

## 1.4 Approach in one paragraph
We froze a calendar-and-pond split with an embargo and a sealed final test; built causal features (only past readings); wrote each experiment's success rule before running it; compared against "same as now" and "same time yesterday"; added conformal ranges and an early-warning probability; explained models with exact TreeSHAP and tested the explanations; replicated the method on a second dataset; and wrapped the result in a plain-language app that refuses to guess when inputs are unreliable.

## 1.5 Contributions (as supported by the evidence)
1. A leakage-controlled, pre-registered evaluation protocol for pond water-quality forecasting, including a one-time sealed test (Chapters 3, 4).
2. Evidence that simple baselines are strong, and a per-case rule that uses a trained model only where it clearly beats them (Chapter 5).
3. Conformal ranges checked on never-seen ponds (Chapter 5).
4. An honest evaluation of a low-oxygen early-warning probability, including a negative result as an alarm (Chapter 5).
5. A stability-and-faithfulness test for SHAP explanations, with 9 of 11 explanations validated (Chapter 6).
6. A replication on a second real dataset showing the evaluation method transfers but the oxygen gains do not (Chapter 5).
7. A serving system with refusal rules and a train/serve parity test that found and fixed a real skew (Chapter 7).

*Note for the author: do not write that any of these is "novel" or "first" until the literature search in Chapter 2 is done properly.*

## 1.6 Structure
Chapter 2 reviews related work. Chapters 3 and 4 describe data and methods. Chapters 5 and 6 give results and explanations. Chapter 7 describes the application. Chapter 8 discusses limits; Chapter 9 concludes.
