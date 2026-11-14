# Chapter 8: Discussion, limits and threats to validity (draft)

## 8.1 What the findings say
1. **Simple guesses are strong.** At 6 hours, the pond's own value from yesterday is as good as, or better than, trained models on never-seen ponds. Reporting accuracy without these baselines would have made the models look far better than they are.
2. **Models help where the near-future matters** (oxygen at 15 minutes and 1 hour; temperature at 1 hour) and the evidence for that survived a sealed test.
3. **What helps differs by environment.** Oxygen gains at Eluru did not appear in the salt marsh, where temperature gains were larger. A single "oxygen forecaster" would be an overclaim.
4. **Quality flags did not help.** The provider's flags are rules computed from the same values, so they add little for tree models.
5. **Honest ranges are possible but conservative** when the test period is calmer than the calibration period.
6. **The alert ranks risk but is not an alarm**, because low oxygen is frequent in these ponds and any useful alarm must fire often.

## 8.2 Threats to validity
- **Small and short data:** 17 ponds in one region over about 9 weeks of one cool season; the sealed test covers four ponds and about ten days. Results may not hold in other seasons, regions, pond types, or longer periods.
- **Pond effects:** only four held-out groups of one to four ponds, so pond-to-pond variation is estimated coarsely.
- **Dataset provenance:** licence unclear; no farm identifiers, so ponds on the same farm may share conditions; there is no aerator, feeding, weather or stocking information.
- **Calibration approximation:** ranges in the final bundle were calibrated on validation errors of earlier (non-final) models; the two switched 6-hour cells were calibrated on validation errors of the plain guess and have not been re-tested.
- **Distribution shift:** validation days were cooler than training days (temperature errors rose); the salt-marsh validation window was winter while most low-oxygen events were in summer.
- **Zeros and sensor faults:** treating exact zeros as faults follows the provider's documentation; in the salt-marsh data about 12% to 18% of oxygen readings were near zero and were kept as real, so the question is not settled.
- **Multiple comparisons:** many cells were tested; 99% intervals were used for the headline rules, but a few borderline intervals (for example oxygen at 6 hours against "yesterday" in validation) lie close to zero.
- **Explanations** describe models, not causes (Chapter 6).
- **Literature:** the related-work chapter has not yet been verified against full texts.

## 8.3 What would strengthen the work
More seasons and farms (the Fish Welfare Initiative request is drafted), aerator and weather records, a live shadow trial with no action taken, retesting `final_v2`, and a calibration scheme for the alert that is checked on a summer validation window.

## 8.4 Ethical note
Forecast errors could mislead a farmer. The app is a research demonstration, refuses when inputs are unreliable, states its limits, and says it does not replace sensors or alarms. Data from the provider were used under unclear licence terms; only derived statistics are published, and permission has been requested.
