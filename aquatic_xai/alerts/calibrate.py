"""Phase 6b: probability calibration and cross-pond-group alert-level selection (no new model fitting)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from aquatic_xai.alerts.evaluate import episode_stats, match_recall_threshold


def fit_isotonic(p: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(np.asarray(p, dtype=float), np.asarray(y, dtype=float))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def false_alarm_flags(rows: pd.DataFrame, score: str, thresh: float) -> pd.DataFrame:
    """One row per pond-day: 1 if any origin with no event in the next window had score >= thresh."""
    r = rows.assign(_fa=((rows["y"] == 0) & (rows[score] >= thresh)).astype(float))
    return r.groupby(["pond", "block_day"], as_index=False)["_fa"].max().rename(columns={"_fa": "fa"})


def choose_level(cal_rows: pd.DataFrame, onsets: dict, score: str, target_recall: float, lead_min: int, lead_max: int) -> tuple[float, dict]:
    """Alert level chosen on calibration rows only."""
    return match_recall_threshold(cal_rows, onsets, score, target_recall, lead_min, lead_max)


def evaluate_level(rows: pd.DataFrame, onsets: dict, score: str, thresh: float, lead_min: int, lead_max: int) -> dict:
    return episode_stats(rows, onsets, score, thresh, lead_min, lead_max)
