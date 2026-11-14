# Chapter 9: Conclusion and future work (draft)

## 9.1 Answers to the research questions
- **RQ1:** Partly. Trained models beat honest baselines for oxygen at 15 minutes and 1 hour and temperature at 1 hour on never-seen ponds, confirmed in a one-time sealed test; at 6 hours, "same time yesterday" is as good or better.
- **RQ2:** No consistent benefit from data-quality information (H1 not supported).
- **RQ3:** Yes in the sense of coverage (never below 91.8% in the final test), but the ranges were usually wider than needed.
- **RQ4:** The probability ranks risky moments better than three simple rules for the next 3 and 6 hours, but it overstates risk and is not usable as an alarm (false alarms on most days).
- **RQ5:** Nine of eleven explanations are stable across seeds, pond groups and time, and faithful; the two that are not are flagged.
- **RQ6:** The evaluation method and system transfer to a second real dataset; the oxygen gains do not.

## 9.2 Main message
In pond water-quality forecasting, the honest question is not "how accurate is the model?" but "what does it add over repeating yesterday?". Answering it with pre-registered rules, leakage controls, never-seen ponds and a sealed test shows a modest, real gain at short range and none at 6 hours, and prevents overclaiming.

## 9.3 Future work
1. More seasons, regions and farms; aerator, feeding, weather and stocking records; a live shadow trial.
2. A neural or probabilistic model (for example a Temporal Fusion Transformer) compared under the same protocol, now that the baselines and rules exist.
3. A better alert: calibrate on a window that includes the low-oxygen season; choose the alert level with farm staff using the cost of a missed crash against a false alarm; evaluate as an alarm in a trial.
4. Physics-guided models of the daily oxygen cycle; reinforcement learning for aeration only if aerator logs become available.
5. Live monitoring (drift, refusals, forecast error and coverage once outcomes arrive) and a tested rollback.
6. Retest `final_v2` and publish the evaluation code and configuration (data subject to licence).
