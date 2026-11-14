# Chapter 4: Methods (draft)

## 4.1 Pre-registration discipline
Before each experiment, its settings and pass/fail rules were written into a configuration file and committed (`configs/*.yaml`). Rules were never changed after seeing results. Every cell is reported, passing or not. The sealed final test was run once, with a lock file and a hash check of the model files (`configs/final_test.yaml`, committed before the run).

## 4.2 Baselines
- **Same as now** (persistence): the latest reading.
- **Same time yesterday** (seasonal naive): the reading one day before the target time (at index g + h − 96, always in the past).
Both use only information available at the origin (unit-tested).

## 4.3 Models
- **Ridge regression** (imputer and scaler fitted on training rows only), **LightGBM** and **XGBoost** with fixed settings (300 trees, learning rate 0.05, no tuning) and three seeds.
- **Quality-blind versus quality-aware** models differ only by the quality feature group (unit-tested), to test H1.
- **Anchored residual model** (Phase 5b): the forecast is an anchor plus a learned correction; the anchor is "same as now" at 15 minutes and 1 hour and "same time yesterday" at 6 hours, with extra past-only daily-pattern features. This fixed two diagnosed weaknesses of level models (they rebuilt the level from scratch, and lacked the pond's daily pattern).
- **Success rule:** per target and distance, the lower end of a 99% blocked-bootstrap interval of the improvement over **both** baselines must be above zero; failed cells use the best simple guess.

## 4.4 Ranges
Split-conformal ranges for a 90% target: the half-width is the conformal quantile of absolute errors calibrated on the **other** pond groups (disjoint ponds). A day/night variant was used where daytime coverage was low.

## 4.5 Low-oxygen early warning
Event: any reading below 2.0 mg/L within the next 1, 3 or 6 hours. The threshold 2.0 mg/L was chosen from descriptive counts only (3 mg/L would fire on 21% of readings). A LightGBM classifier with the same fixed settings; three simple scoring rules for comparison (current level, trend extrapolation, the same window yesterday); metric: average precision with blocked bootstrap; calibration by isotonic regression fitted on other pond groups; episode-level evaluation (is an alert raised 1 to 6 hours before an episode starts; false-alarm pond-days) with the alert level chosen on other pond groups.

## 4.6 Explanations (Phases 7 and 8)
Exact TreeSHAP (LightGBM's built-in contributions) on the models that helped. For forecasts, SHAP explains the correction to the anchor. Pre-registered tests of the explanations: **E1** rank stability across three seeds (≥ 0.90), **E2** stability across held-out pond groups (≥ 0.70 and ≥ 3 shared top-5 inputs), **E3** stability across time halves (≥ 0.70), **E4** faithfulness: replacing the top-5 inputs (chosen on training rows) with training medians must hurt more than replacing five random inputs (99% interval above zero in the main model and at least 3 of 4 pond-group models).

## 4.7 Replication protocol (Phase 1b-R)
The same pipeline on the salt-marsh data with its own frozen split (calendar cut-offs, 12-hour embargo, one sealed pond, leave-one-pond-out folds), a 30-minute grid and quality-blind models only. Method "replicates" if at least 3 of 9 forecast cells beat both baselines, including at least one 6-hour cell.

## 4.8 Serving system (Phases 9 and 10)
Input checks, refusal rules, an input-range guard, versioned model bundles with file hashes, and a **train/serve parity test**: for the same moment, the app (fed only raw readings through the HTTP API) must give the same numbers as the research pipeline.

## 4.9 Reproducibility
All compute ran on Modal (CPU) with a pinned image; each experiment has an id derived from configuration and data versions; reruns in two separate containers give bit-identical results; all code and configuration are in the repository (branches `research/init` and `research/phase6b-external-data`); no raw data is committed.
