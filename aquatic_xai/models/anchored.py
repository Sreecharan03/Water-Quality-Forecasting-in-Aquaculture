"""Phase 5b anchored-residual forecast: forecast = anchor + learned correction.
Anchor: 'same as now' at 15 min and 1 h; 'same time yesterday' at 6 h (falls back to 'same as now' if yesterday is missing)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.models.tabular import feature_columns


def anchor_for(df: pd.DataFrame, var: str, h: int, anchor_kind: str) -> tuple[np.ndarray, np.ndarray]:
    """Returns (anchor values, used_fallback flag). Uses only columns known at the origin."""
    cur = df[f"{var}_cur"].to_numpy(dtype=float)
    if anchor_kind == "persistence":
        return cur, np.zeros(len(df), dtype=bool)
    yd = df[f"{var}_yday_tgt_h{h}"].to_numpy(dtype=float)
    fb = np.isnan(yd)
    return np.where(fb, cur, yd), fb


def anchored_columns(base_specs: list[dict], daily: list[dict], var: str, h: int, aware: bool, anchor_kind: str) -> list[str]:
    cols = feature_columns(base_specs, aware) + [s["name"] for s in daily
                                                  if "_yday_tgt_h" not in s["name"] or s["name"] == f"{var}_yday_tgt_h{h}"]
    return cols


def add_anchor_gap(df: pd.DataFrame, var: str, anchor: np.ndarray) -> np.ndarray:
    """Extra feature for yesterday-anchored models: anchor minus current reading (trees cannot subtract by themselves)."""
    return anchor - df[f"{var}_cur"].to_numpy(dtype=float)
