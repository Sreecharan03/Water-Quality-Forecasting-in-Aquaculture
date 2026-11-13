"""Forward-chronological windows with an embargo. All ponds share the same calendar cutoffs."""
from __future__ import annotations

import numpy as np
import pandas as pd


def choose_cutoffs(ts: pd.Series, fractions: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Calendar-midnight cutoffs T1 < T2 where the share of origins reaches the train and train+val fractions."""
    s = pd.Series(pd.to_datetime(ts)).sort_values().reset_index(drop=True)

    def at(q: float) -> pd.Timestamp:
        return s.iloc[int(np.floor(q * (len(s) - 1)))].normalize()

    t1, t2 = at(fractions["train"]), at(fractions["train"] + fractions["val"])
    if not t1 < t2:
        raise ValueError("cutoffs are not increasing")
    return t1, t2


def window_labels(ts: pd.Series, t1: pd.Timestamp, t2: pd.Timestamp, embargo: pd.Timedelta) -> np.ndarray:
    """train | embargo_train_val | val | embargo_val_test | test, by origin timestamp.
    With embargo >= lookback + horizon, no train target window touches a validation feature window."""
    if not t1 + embargo < t2:
        raise ValueError("embargo does not fit between cutoffs")
    ts = pd.to_datetime(ts)
    lab = np.full(len(ts), "test", dtype=object)
    lab[(ts <= t2 + embargo).to_numpy()] = "embargo_val_test"
    lab[(ts <= t2).to_numpy()] = "val"
    lab[(ts <= t1 + embargo).to_numpy()] = "embargo_train_val"
    lab[(ts <= t1).to_numpy()] = "train"
    return lab
