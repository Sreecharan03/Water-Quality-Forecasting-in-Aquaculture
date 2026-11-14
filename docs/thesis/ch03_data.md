# Chapter 3: Data and evaluation design (draft)

## 3.1 Primary dataset
Fish Welfare Initiative "Data-Campaign": 17 continuous pond series (CSV), one reading about every 15 minutes, 28 November 2025 to 30 January 2026, Eluru, Andhra Pradesh, India, in IST. Variables used: dissolved oxygen (mg/L), pH, water temperature (°C). Four further ponds have only handheld readings and were excluded. The dataset commit is pinned and each file is verified by its blob hash. **Licence unclear**: only citation and derived statistics are published; no raw data is in the repository (see `docs/data_card.md`, and the draft request in `docs/outreach/`).

## 3.2 Cleaning policy (mask, never delete)
- Exact zeros are treated as equipment artefacts (the provider documents this) and masked.
- Values outside physical limits are masked.
- Conflicting duplicate timestamps are masked per variable and quarantined.
- Quality flags from the provider are parsed to true/false and kept as features; they do not mask values.
- Nothing is interpolated or filled.
The processed dataset has a version hash; reruns reproduce identical content hashes.

## 3.3 Causal features
At each 15-minute origin, features use only readings at or before it: current value, six lags (15 minutes to 6 hours), trailing mean, minimum, maximum and standard deviation over 1, 3 and 6 hours, a 3-hour trend, time of day (sine and cosine), and groups describing data quality (age of the last valid reading, share valid, flag counts). Targets are the real reading at +15 minutes, +1 hour and +6 hours; if none exists the target is empty. Two leakage tests ran on the real tables: *prefix invariance* (recomputing features from history truncated at the origin gives identical values) and *independent target alignment* (targets re-derived by timestamp lookup). Phase 5b added past-only daily-pattern features (yesterday's value at the target time, trailing 24-hour statistics); the same tests were repeated.

## 3.4 The frozen split
- Calendar cut-offs shared by all ponds: training to 2026-01-10, validation to 2026-01-20, test after. A 12-hour embargo (6-hour look-back plus 6-hour horizon) separates windows.
- **Four sealed ponds**, drawn at random with seed 20261113 from 15 eligible ponds, never used until the final test; 13 development ponds in four grouped folds (one pond is training-only).
- Eleven evaluation regimes, including *future days on seen ponds*, *future days on unseen ponds* (the realistic case), and *same days on unseen ponds* (shown to be optimistic).
- Confidence intervals use a blocked bootstrap with blocks of pond by calendar day.
Independence checks (no row or pond overlap, embargo gap of at least zero) pass for all regimes.

## 3.5 Second dataset
BCO-DMO 988873: five tidal salt-marsh ponds in New Jersey, April 2023 to June 2024, oxygen, pH and temperature every 10 minutes, CC BY 4.0, verified by checksum. It is a **different environment** (sea-water salinity, temperate climate, no feeding or aeration), so it tests whether the *method* transfers, not whether the Eluru models do. Data of two other candidates (AquaSustain-Bench, AquaSense) were opened and found to be **synthetic**, so they were rejected and are not used as evidence (`docs/external_data_decision.md`). For this dataset, readings were subsampled to a 30-minute grid because 10-minute data cannot reach a 15-minute grid without interpolation; one pond (Shark) and the last window were sealed.

## 3.6 Descriptive facts worth stating
- Eluru development ponds: 13.4% of oxygen readings below 2 mg/L; median daily oxygen swing 12.8 mg/L; temperature 21 to 31 °C (middle 90%: 24.1 to 27.5).
- Salt marsh: 25.1% below 2 mg/L; median daily swing 4.4 to 8.9 mg/L by pond; temperature from −1.8 to 36 °C.
- Eluru data span about 7.5 weeks in one cool period, so seasonal behaviour is unknown.
