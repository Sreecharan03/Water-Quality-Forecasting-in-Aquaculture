# Chapter 2: Related work (DRAFT SKELETON: must be rewritten after reading the papers)

> **Warning.** Everything below comes from search summaries, not from reading the full papers (see `docs/literature_matrix.md`). Before submitting, read each paper, check each statement, add page numbers, and add the missing citations. The statements are reminders of what to look for, not claims you can cite yet.

## 2.1 Deep learning for dissolved oxygen in aquaculture
The search found a number of 2025 and 2026 papers using Transformers, CNN-Transformer hybrids and recurrent hybrids for dissolved-oxygen prediction in aquaculture (matrix rows 2 to 4). *To check:* which datasets they use, whether testing used unseen ponds or only later times, and whether they compare against "same as now".

## 2.2 Persistence is hard to beat
One 2025 study of aquaponic fish ponds that forecast pH, temperature and oxygen together reportedly found that a persistence baseline still beat a Transformer on short-term oxygen and pH errors (matrix row 1). If confirmed in the full text, this is the closest published precedent for our Chapter 5 finding, and should be discussed in detail.

## 2.3 Interpretability
A 2025 ensemble paper notes that interpretability is often missing in deep aquaculture models (matrix row 5). A Temporal Fusion Transformer paper on aquaponics reports built-in variable selection and attention (row 6). *To check:* whether any aquaculture paper tests the stability and faithfulness of explanations, as in our Chapter 6.

## 2.4 Uncertainty and hypoxia early warning
Cerqueira et al. (2024) frame fish-farm hypoxia as a threshold-exceedance probability (row 9); a 2026 coastal hypoxia benchmark uses the same 2.0 mg/L level that we chose (row 10). Conformal prediction has been used for water-demand intervals (row 13). *To check:* whether conformal ranges have been applied to pond water-quality forecasts.

## 2.5 Foundation models, physics-guided learning, control
Time-series foundation models (row 7, 8) and process-guided learning for lake oxygen (row 12) are possible directions. Reinforcement learning for aeration (row 11) needs aerator logs that our dataset lacks. These are future work.

## 2.6 Gap statement (to be written only after a proper search)
Do **not** claim a gap yet. Run a systematic search (Scopus, Web of Science, Google Scholar, arXiv), record queries and dates, then state exactly what is and is not covered. Candidate wording once verified: "To our knowledge, ..." with the search dates.
