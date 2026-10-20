# Data Card: FWI Continuous Monitoring (Data Campaign)

All numbers below come from Modal run `ap-WsR1xtMo6ZZp1pSxk4Awt9` and diagnostics run `ap-RpMfN8Y7lNJSURWZZablub` (workspace `jhansimary143`). Full tables: `/artifacts/reports/phase1/4cfa138e725db541e7ae14b89170909bef7dafb1/inventory.{md,json}` on the Modal volume `aquatic-xai-artifacts`.

## Provenance
| Item | Value |
|---|---|
| Source | https://github.com/fish-welfare-initiative/Data-Campaign-Data |
| Pinned commit | `4cfa138e725db541e7ae14b89170909bef7dafb1` |
| Retrieved (UTC) | 2026-10-20T13:29:04 |
| Files ingested | 23 (17 pond CSVs, 5 reference sheets, README), 2,983,335 bytes |
| Integrity | Every file's size and git blob SHA matched GitHub's tree listing; SHA256 stored in `/data/manifests/raw_fwi-data-campaign_<sha>.json` |
| Storage | Modal Volume `aquatic-xai-data`, `/data/raw/fwi-data-campaign/<sha>/` (nothing on the local machine) |
| Licence | **Unclear.** README asks for citation only; no LICENSE file. Raw data not committed to GitHub. |
| Citation | Fish Welfare Initiative, Continuous Water Quality Monitoring Data (Data Campaign), Eluru, Andhra Pradesh, Nov 2025 – Jan 2026 |

## Schema (verified from file)
`Date/Time (IST)`, `DO (mg/L)`, `pH`, `Temperature (°C)`, `QC_Flag_DateTime`, `QC_Flag_DO`, `QC_Flag_pH`. Timestamps are naive local time labelled IST (UTC+05:30, no DST), no offset marker in the strings. Units are labelled in the headers; DO is mg/L, not % saturation.

## Size and coverage
- 17 ponds, 72,750 rows in total; 26–63 days per pond (median about 48), mostly 2025-12-14 to 2026-01-30.
- Four more ponds in Key_Events (`ara2_e985ca4a`, `6857ac3f`, `1d5dce9e`, `f5e499f4`) were measured with handheld ProDSS only and have **no continuous series**; they are not usable for forecasting.
- Intervals: 95.7–99.2% of steps are within 1 minute of 15 min. No rows are off the 15-min grid (tolerance 3 min).

## Known quality issues (counted, not yet treated)
1. **Zero readings** (equipment artifacts per FWI): mostly 2026-01-07/08 (many ponds), pond `3ed4df8e` (95 rows), pond `ca187575` (495 pH zeros after 25 Jan), and 26–30 Jan (about 93–96 rows/day).
2. **Conflicting duplicate timestamps** in 2 ponds: `3ed4df8e` (220 timestamps) and `6ca69422` (34). Every duplicate pair has different values (e.g. pH 9.09 vs 8.5 at the same instant). Cause unknown (two devices? re-upload?). Keeping "first" would be arbitrary.
3. **Gaps >20 min**: 3,010 flagged; 31–209 per pond; longest 233 h (`3b2f3973`), 183 h (`0677080b`). Hot spots: 10 Dec, 17 Dec, 22 Dec, 25 Dec.
4. **Calibration events** on 8–9 Jan 2026 for 16 of 17 devices (Key_Events). A possible structural break in sensor behaviour at this date.
5. **Harvest/reinstall breaks** (`3b2f3973`, `ca187575`, `6ca69422`, `858b914c`); a damaged pH bulb on `29660d32` (29 Dec); device silent 18–25 Jan on `0677080b`.
6. **Implausible values to review**: DO up to 25.6 mg/L, Temp up to 36.0 °C and 33.5 °C, pH minimum 5.3. Some are probably real (supersaturation) and some probe artifacts; not decided.
7. **QC flags** cover time gaps, DO < 0.1, DO jump > 2, DO > 10 before noon, pH out of range, pH jump > 1; zeros are NOT flagged. Several flags are computed from the value itself.
8. Cleaning cycle (about every 5 days) causes fouling drift not represented by flags.

## Intended use and limits
Research on 15 min–6 h forecasting of DO, pH and temperature. About 7 weeks of one winter season in one district: results must not be generalized to other seasons, regions, species or management regimes.
