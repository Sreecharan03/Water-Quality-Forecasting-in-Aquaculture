"""Low-oxygen alert labels and the causal 'what happened in this window yesterday' feature.

Label at origin g for window W: does any valid DO reading in (g, g+W] fall below the threshold?
 - True  if at least one valid reading is below the threshold (the event definitely happened)
 - False if no valid reading is below AND at least half of the W slots have a valid reading
 - NaN   otherwise (not enough observations to say)
Feature (known at g): minimum DO in the same window one day earlier, i.e. over (g-96, g-96+W]; its indices are <= g-72.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DAY = 96


def _full(pond_table: pd.DataFrame, col: str = "DO_cur") -> pd.Series:
    n = int(pond_table["grid_idx"].max()) + 1
    s = pd.Series(np.nan, index=np.arange(n))
    s.loc[pond_table["grid_idx"].to_numpy()] = pond_table[col].to_numpy(dtype=float)
    return s


def _forward_min(full: pd.Series, W: int) -> tuple[pd.Series, pd.Series]:
    fut = full.shift(-1)[::-1]                       # reversed so a trailing window = the next W slots
    mn = fut.rolling(W, min_periods=1).min()[::-1]
    nv = fut.notna().astype(float).rolling(W, min_periods=1).sum()[::-1]
    return mn, nv


def window_labels(pond_table: pd.DataFrame, W: int, thr: float, day: int = DAY) -> tuple[np.ndarray, np.ndarray]:
    """Returns (label as float: 1/0/NaN, yesterday-window minimum) aligned to pond_table rows."""
    full = _full(pond_table)
    mn, nv = _forward_min(full, W)
    event = mn < thr
    known_no = (~event) & (nv >= int(np.ceil(W / 2)))
    lab = pd.Series(np.where(event, 1.0, np.where(known_no, 0.0, np.nan)), index=full.index)
    yday = mn.shift(day)                              # window one day earlier: only indices <= g - (day - W)
    g = pond_table["grid_idx"].to_numpy()
    return lab.reindex(g).to_numpy(), yday.reindex(g).to_numpy()


def add_alert_columns(T: pd.DataFrame, windows: dict, thr: float, day: int = DAY) -> pd.DataFrame:
    """Adds lab_W{W} (a target, NOT a feature) and ydaymin_W{W} (a feature) for every window, pond by pond."""
    cols = {}
    for W in windows.values():
        lab, yd = np.full(len(T), np.nan), np.full(len(T), np.nan)
        for _, g in T.groupby("pond", sort=False):
            pos = T.index.get_indexer(g.index)
            lab[pos], yd[pos] = window_labels(g, W, thr, day)
        cols[f"lab_W{W}"], cols[f"ydaymin_W{W}"] = lab, yd
    return pd.concat([T, pd.DataFrame(cols, index=T.index)], axis=1)


def episode_onsets(pond_table: pd.DataFrame, thr: float, quiet: int = 24) -> np.ndarray:
    """Grid indices where DO first drops below thr after at least `quiet` slots with no valid reading below thr."""
    full = _full(pond_table)
    below = (full < thr).to_numpy()
    last = -10**9
    out = []
    for i in np.where(below)[0]:
        if i - last > quiet:
            out.append(i)
        last = i
    return np.array(out, dtype=int)
