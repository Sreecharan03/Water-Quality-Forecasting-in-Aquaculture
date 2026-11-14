# Thesis pack: outline and status

**Title (fixed):** An aquatic model for water quality prediction and interpretation using explainable AI

Written for: you (the M.Tech student) and your guide, as drafts to edit. Every number comes from a report in this repository; nothing is invented. Where something is unverified, it says so.

## Files
| File | Content | State |
|---|---|---|
| `abstract.md` | One-page abstract | draft |
| `ch01_introduction.md` | Problem, questions, contributions | draft |
| `ch02_literature.md` | Related work | **draft with a warning: papers not yet read in full** |
| `ch03_data.md` | Datasets, cleaning, features, split | draft |
| `ch04_methods.md` | Models, ranges, alert, explanations, evaluation rules | draft |
| `ch05_results.md` | All results, including negative ones | draft |
| `ch06_explanations.md` | SHAP and its validation | draft |
| `ch07_system.md` | The app and its safety checks | draft |
| `ch08_discussion.md` | What it means, limits, threats to validity | draft |
| `ch09_conclusion.md` | Conclusions and future work | draft |
| `viva_qa.md` | 30 likely questions with honest answers | draft |
| `claims_table.md` | What you may and may not claim | draft |
| `figures/` | Three figures from the final test | built |

## Chapter map to the evidence in the repository
| Chapter | Evidence |
|---|---|
| 3 Data | docs/data_card.md, docs/phases/PHASE_01 to 04, docs/external_data_decision.md |
| 4 Methods | configs/*.yaml (contracts written before runs) |
| 5 Results | docs/phases/PHASE_05, 05b, 06, 06b, 01b_R, 11; docs/experiments/*.md |
| 6 Explanations | docs/phases/PHASE_07, 08; docs/experiments/exp-570e678b7197_explanations.md |
| 7 System | docs/phases/PHASE_09, 10; docs/app_runbook.md |

## What only you can do (I cannot)
1. Fill in names, university, guide, programme, dates, acknowledgements, declaration, and ethics statement.
2. **Read the papers** in `docs/literature_matrix.md` in full and rewrite Chapter 2 from what they actually say. Do not claim novelty ("first", "no one has") until you have done a proper search and your guide agrees.
3. Check the dataset licence situation (email to the Fish Welfare Initiative is drafted in `docs/outreach/`).
4. Decide with your guide whether the thesis presents the project as: (a) a rigorous evaluation study with an explainable forecasting system, which is what the evidence supports; or (b) a "high-accuracy model", which the evidence does not support.
5. Have the figures and tables checked against `docs/experiments/final_test_report.md` before printing.

## Suggested length
About 60 to 80 pages once figures, tables, references and appendices are added.
