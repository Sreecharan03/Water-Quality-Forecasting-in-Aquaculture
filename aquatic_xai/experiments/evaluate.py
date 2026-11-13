"""Blocked bootstrap (unit = pond x calendar day) for means, paired differences and relative improvement."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _blocks(d: pd.DataFrame, cols: list[str]) -> np.ndarray:
    g = d.groupby(["pond", "block_day"])
    return np.column_stack([g[c].sum().to_numpy() for c in cols] + [g.size().to_numpy()])


def _resample(n_blocks: int, B: int, seed: int) -> np.ndarray:
    return np.random.RandomState(seed).randint(0, n_blocks, size=(B, n_blocks))


def mean_ci(d: pd.DataFrame, col: str, B: int = 2000, seed: int = 0) -> tuple[float, float, float, int]:
    d = d.dropna(subset=[col])
    if d.empty:
        return (np.nan,) * 3 + (0,)
    b = _blocks(d, [col])
    idx = _resample(len(b), B, seed)
    stats = b[idx, 0].sum(1) / b[idx, 1].sum(1)
    return float(b[:, 0].sum() / b[:, 1].sum()), float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5)), int(len(d))


def diff_ci(d: pd.DataFrame, a: str, b: str, B: int = 2000, seed: int = 0) -> tuple[float, float, float, int]:
    """Mean of (a - b) over common rows. Negative = a has the smaller error."""
    d = d.dropna(subset=[a, b]).copy()
    d["_diff"] = d[a] - d[b]
    return mean_ci(d, "_diff", B, seed)


def improvement_ci(d: pd.DataFrame, model: str, ref: str, B: int = 2000, seed: int = 0) -> tuple[float, float, float, int]:
    """1 - sum|err_model| / sum|err_ref| over common rows; positive = model is better than ref."""
    d = d.dropna(subset=[model, ref])
    if d.empty:
        return (np.nan,) * 3 + (0,)
    b = _blocks(d, [model, ref])
    idx = _resample(len(b), B, seed)
    stats = 1 - b[idx, 0].sum(1) / b[idx, 1].sum(1)
    return float(1 - b[:, 0].sum() / b[:, 1].sum()), float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5)), int(len(d))


def fmt(est_lo_hi_n, pct: bool = False, digits: int = 3) -> str:
    est, lo, hi, _ = est_lo_hi_n
    if np.isnan(est):
        return "n/a"
    if pct:
        return f"{est*100:+.1f}% [{lo*100:+.1f}, {hi*100:+.1f}]"
    return f"{est:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"
