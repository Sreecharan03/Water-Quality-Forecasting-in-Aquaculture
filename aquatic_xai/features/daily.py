"""Phase 5b past-only daily-pattern features ("daily" group), added on top of the Phase 3 table.

Everything at origin index g uses grid points <= g only:
- {v}_d1            = reading at g-96 (same time yesterday as the origin)
- {v}_dmean96/min/max = trailing 24 h statistics including g
- {v}_yday_tgt_h{h} = reading at g+h-96, i.e. one day before the TARGET time; for h <= 24 that index is <= g-72
Absent grid slots count as missing (NaN), exactly as on the Phase 3 grid.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DAILY_CODE_VERSION = "daily-v1"
VARS = ["DO", "pH", "Temp"]
DAY = 96


def daily_columns(horizons: list[int]) -> list[str]:   # column names do not depend on the day length
    c = []
    for v in VARS:
        c += [f"{v}_d1", f"{v}_dmean96", f"{v}_dmin96", f"{v}_dmax96"] + [f"{v}_yday_tgt_h{h}" for h in horizons]
    return c


def daily_features(pond_table: pd.DataFrame, horizons: list[int], day: int = DAY) -> pd.DataFrame:
    """pond_table: one pond's Phase 3 rows (columns grid_idx, DO_cur, pH_cur, Temp_cur). Returns daily columns, same row order."""
    g = pond_table["grid_idx"].to_numpy()
    n = int(g.max()) + 1
    out = {}
    for v in VARS:
        full = pd.Series(np.nan, index=np.arange(n))
        full.loc[g] = pond_table[f"{v}_cur"].to_numpy(dtype=float)
        r = full.rolling(day, min_periods=1)
        cols = {f"{v}_d1": full.shift(day), f"{v}_dmean96": r.mean(), f"{v}_dmin96": r.min(), f"{v}_dmax96": r.max()}
        for h in horizons:
            assert day - h >= 0, "reference reading must not be in the future"
            cols[f"{v}_yday_tgt_h{h}"] = full.shift(day - h)       # value at index g + h - day
        for k, s in cols.items():
            out[k] = s.reindex(g).to_numpy()
    return pd.DataFrame(out, index=pond_table.index)


def daily_specs(horizons: list[int]) -> list[dict]:
    return [{"name": c, "group": "daily"} for c in daily_columns(horizons)]


def prefix_invariance_daily(pond_table: pd.DataFrame, horizons: list[int], rows: np.ndarray, day: int = DAY) -> dict:
    """Recompute daily features from a table truncated at the origin; they must equal the full-table values."""
    full = daily_features(pond_table, horizons, day)
    cols = list(full.columns)
    bad, max_diff = 0, 0.0
    for r in rows:
        g = pond_table.loc[r, "grid_idx"]
        pre = pond_table[pond_table["grid_idx"] <= g]
        a = daily_features(pre, horizons, day).loc[r, cols].to_numpy(dtype=float)
        b = full.loc[r, cols].to_numpy(dtype=float)
        d = float(np.nanmax(np.abs(a - b))) if np.isfinite(a).any() else 0.0
        max_diff = max(max_diff, d)
        if not np.array_equal(np.isnan(a), np.isnan(b)) or d > 1e-9:
            bad += 1
    return {"origins_checked": int(len(rows)), "features_checked": len(cols), "mismatching_origins": bad, "max_abs_diff": max_diff}
