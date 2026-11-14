# Literature matrix (working draft)

**Verification status:** every row below was found through web-search summaries (titles, abstracts or snippets). **None of the full texts has been read yet.** Statements marked "reported" must be checked against the full paper before they go into the thesis. No result from this table is used as a claim about our own data.

Search date: 2026-11-13. Search was limited and not exhaustive.

| # | Paper (as listed) | Topic | What it reports (from the snippet) | Why it matters to us | Verified? |
|---|---|---|---|---|---|
| 1 | Transformer-Based Modeling on Multi-Target Water Quality Forecasting in Aquaponic Fish Ponds (MDPI Water, 2025) | Multi-target pH, temperature, DO forecasting | A simple persistence baseline beat the Transformer on short-term DO and pH; the Transformer was the best learned model | Same pattern as our Phase 5: persistence is hard to beat at short range. Supports honest baselines. | No (snippet) |
| 2 | Hybrid deep learning framework for real-time DO prediction in aquaculture (Scientific Reports, 2025) | DO forecasting, deep learning | Hybrid deep model for DO | Deep-learning baseline family | No |
| 3 | Improving multi-step DO prediction in aquaculture using adaptive temporal convolution and optimized transformer (Computers and Electronics in Agriculture, 2025) | Multi-step DO | Temporal convolution + Transformer; authors say it can extend to pH | Multi-step comparison | No |
| 4 | Compressive CNN and transformer hybrid for long-term DO prediction in aquaculture (ScienceDirect, 2026) | Long-horizon DO | CNN handles local features from sparse sensors, Transformer handles long range | Long-horizon DO | No |
| 5 | IoT-driven ensemble machine learning for DO prediction in aquaculture (ResearchGate, 2025) | DO, ensembles | States that interpretability is often missing in deep models | Supports our explainability motivation | No |
| 6 | Temporal Fusion Transformer-based prediction in aquaponics (Springer, J. Supercomputing) | Nitrate forecasting with TFT | TFT with variable selection and interpretable attention, compared with LSTM variants | Candidate for a later interpretable deep model | No |
| 7 | Benchmarking Foundation Models for Time-Series Forecasting: zero-shot, few-shot, full-shot (2025) | Chronos, TimesFM, Moirai | Chronos-Bolt variants among the best in zero-shot | Possible future baseline (not planned now) | No |
| 8 | Beyond Accuracy: Are Time Series Foundation Models Well-Calibrated? (arXiv 2510.16060) | Calibration of foundation models | Foundation models can be over- or under-confident | Motivates checking calibration, as we do for ranges | No |
| 9 | Probabilistic hypoxia forecasting for fish farms (Frontiers in Aquaculture, 2024, Cerqueira et al.) | Probability of DO below a threshold | Frames hypoxia as threshold-exceedance probability | Closest precedent for our alert (Phase 6) | No |
| 10 | Benchmarking AI models for daily coastal hypoxia forecasting (arXiv 2602.05178) | Coastal hypoxia classification | BiLSTM, Transformer, TCN compared for DO <= 2.0 mg/L | Uses the same 2.0 mg/L level we chose; different setting (coastal, daily) | No |
| 11 | RL-based predictive control for aquaculture water quality (WAS 2025 abstract) | Aerator control with RL | Reported ~90% of cycles in safe range, ~25% energy saving (abstract only) | Why RL is future work: needs aerator logs we do not have | No |
| 12 | Adaptive Process-Guided Learning: lake DO (arXiv 2411.12973) | Physics-guided RNN for DO | Adds the DO equation to the loss | Possible future direction (physics-guided) | No |
| 13 | Conformal prediction for water demand (EGU24-8166, Wewer and Taormina) | Conformal intervals in water systems | Conformal prediction is model agnostic with coverage guarantees under assumptions | Method precedent for our ranges | No |

## Gaps the search suggests (to verify)
- Searches did not find a paper that applies SHAP or attention attribution to Transformer-based DO or pH forecasts in aquaculture, and did not find conformal ranges applied to pond DO forecasting. **This may be a search limitation, not a confirmed gap.** It must be checked with a proper search before any novelty claim is written.

## To do
1. Read the full text of rows 1, 6, 9 and 10 first.
2. Repeat the search on Google Scholar, Scopus and arXiv with several phrasings; record queries and dates.
3. Add the dataset paper or documentation for the Fish Welfare Initiative data once its licence is clarified.

## Correction (2026-11-14)
AquaSustain-Bench (Zenodo 10.5281/zenodo.21249767) and AquaSense (Mendeley fhnb2h7hyc) were checked: their released sensor data is **synthetic** (see docs/external_data_decision.md). Do not cite either as evidence about real ponds. Row 12 and earlier mentions of AquaSustain in conversation were based on descriptions, not on the files.
