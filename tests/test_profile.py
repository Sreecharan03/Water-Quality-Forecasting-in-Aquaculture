"""Hand-computed toy fixtures (synthetic, unit-test only; never research data)."""
import numpy as np
import pandas as pd

from aquatic_xai.data.ingest import git_blob_sha
from aquatic_xai.data.profile import profile_pond, usable_origins

CFG = {"nominal_interval_min": 15, "gap_threshold_min": 20, "grid_tolerance_min": 3,
       "horizons_steps": [1, 2], "lookback_steps": [2]}


def test_usable_origins_hand_computed():
    valid = np.array([1, 1, 1, 0, 1, 1, 1, 1], dtype=bool)
    # lookback 2, horizon 1: origins g=1..6 need valid[g-1],valid[g] and valid[g+1]
    # g=1 ok (0,1 valid; 2 valid) ; g=2 -> needs valid[3] False ; g=3 no ; g=4 needs valid[3]: no
    # g=5 ok ; g=6 ok
    assert usable_origins(valid, valid, lookback=2, horizon=1) == 3


def test_git_blob_sha_known_value():
    assert git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def _frame(ts, do, ph, t):
    return pd.DataFrame({"Timestamp": ts, "DO (mg/L)": do, "pH": ph, "Temperature (°C)": t})


def test_profile_counts_zero_gap_and_duplicates_without_dropping():
    ts = ["2025-11-01 00:00:00", "2025-11-01 00:15:00", "2025-11-01 00:15:00",
          "2025-11-01 00:30:00", "2025-11-01 01:30:00", "2025-11-01 01:45:00"]
    df = _frame(ts, [5, 5, 5, 0, 6, 6], [7, 7, 7, 7, 7, 7], [28, 28, 28, 28, 28, 28])
    p = profile_pond(df, CFG)
    assert p["n_rows"] == 6                       # nothing dropped from the raw count
    assert p["n_duplicate_timestamps"] == 1
    assert p["targets"]["DO"]["n_zero"] == 1
    assert p["gaps"]["n_gaps_over_threshold"] == 1
    assert p["gaps"]["max_gap_hours"] == 1.0
    assert p["n_rows_all_three_valid"] == 4       # 0 DO row excluded from "valid", not deleted


def test_out_of_order_detected():
    df = _frame(["2025-11-01 00:15:00", "2025-11-01 00:00:00", "2025-11-01 00:30:00"],
                [5, 5, 5], [7, 7, 7], [28, 28, 28])
    assert profile_pond(df, CFG)["n_out_of_order"] == 1
