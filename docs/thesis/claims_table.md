# What you may and may not claim

| You may say | Evidence | Wording tip |
|---|---|---|
| Trained models clearly beat "same as now" and "same time yesterday" for oxygen at 15 min and 1 h, and temperature at 1 h, on 4 never-seen ponds | Phase 11 | "in a sealed test on four ponds over about ten days" |
| At 6 hours, "same time yesterday" was as good as or better than the model | Phase 11 | state it as a finding, not a failure to hide |
| Data-quality information did not help consistently | Phases 5, 5b | "H1 was not supported" |
| Conformal ranges never fell below 91.8% coverage in the sealed test, but were wide | Phase 11 | "valid but conservative" |
| The low-oxygen probability ranks risk better than three simple rules for the next 3 and 6 hours | Phase 11 | "ranking, not an alarm" |
| 9 of 11 explanations passed pre-registered stability and faithfulness tests | Phase 8 | "tests fixed in advance" |
| The evaluation method transferred to a second real dataset; oxygen gains did not | Phase 1b-R | "weak replication" |
| The app matches the research pipeline exactly and refuses unreliable inputs | Phase 10 | "train/serve parity test" |

| You may NOT say | Why |
|---|---|
| "The model predicts oxygen with X% accuracy" | We report average miss against baselines; there is no single accuracy |
| "First", "novel", "no one has done this" | Literature search not done or verified |
| "The alert warns farmers reliably" | False alarms on 98% of pond-days at the tested level; percentages overstated |
| "Works for any pond / season / region" | One region, one cool season; the second dataset showed differences |
| "The explanations show what causes low oxygen" | They describe the model |
| "The system is production-ready / safe for farms" | Not deployed, no live trial, evidence gates in `docs/production_plan.md` not met |
| "`final_v2` was tested" | Only `final_v1` was tested; the two switched cells were not re-tested |
| "Quality information improves forecasts" | Not supported |
| "AquaSustain-Bench or AquaSense confirm our results" | Their released data is synthetic |
