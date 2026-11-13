"""Tier-0 baselines. Both use only data at or before the origin time."""
from __future__ import annotations

import numpy as np
import pandas as pd


def persistence(df: pd.DataFrame, var: str) -> np.ndarray:
    """Forecast = the latest reading ("same as now")."""
    return df[f"{var}_cur"].to_numpy(dtype=float)


def seasonal_naive(full: pd.DataFrame, rows: pd.DataFrame, var: str, h: int, steps_per_day: int = 96) -> np.ndarray:
    """Forecast for t+h = the reading one day before the target time, i.e. at grid index g + h - steps_per_day
    (always <= g for h <= steps_per_day, so it is known at the origin). NaN when that reading does not exist."""
    key = full.set_index(["pond", "grid_idx"])[f"{var}_cur"]
    idx = pd.MultiIndex.from_arrays([rows["pond"].to_numpy(), rows["grid_idx"].to_numpy() + h - steps_per_day])
    return key.reindex(idx).to_numpy(dtype=float)
