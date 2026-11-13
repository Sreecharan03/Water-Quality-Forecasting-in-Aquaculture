"""Hand-computed toy fixtures (synthetic, unit-test only; never research data)."""
import numpy as np
import pandas as pd

from aquatic_xai.data.clean import VAR_FLAG_COLS
from aquatic_xai.features.build import FLAG_SOURCE_COLS, compute_features, make_targets
from aquatic_xai.features.dictionary import feature_specs

CFG = {"variables": ["DO", "pH", "Temp"], "lags": [1, 2, 4], "windows": [2, 4], "slope_window": 4,
       "age_cap": 10, "flag_lookback": 4, "warmup_steps": 4, "horizons": [1, 2]}


def toy_grid(do, present=None, n=None):
    n = n or len(do)
    g = pd.DataFrame({"present": present if present is not None else [True] * n})
    g["ts"] = pd.Timestamp("2025-12-01 00:00") + pd.to_timedelta(np.arange(n) * 15, unit="m")
    g["DO"] = np.asarray(do, dtype=float)
    g["pH"] = 8.0
    g["Temp"] = 26.0
    for c in FLAG_SOURCE_COLS:
        g[c] = False
    return g


def test_lags_are_past_values_and_hand_computed():
    f = compute_features(toy_grid([1, 2, 3, 4, 5, 6]), CFG)
    assert f.loc[5, "DO_cur"] == 6 and f.loc[5, "DO_lag1"] == 5 and f.loc[5, "DO_lag4"] == 2
    assert np.isnan(f.loc[1, "DO_lag4"])                      # not enough history: NaN, never backfilled


def test_trailing_rolling_includes_origin_only_past():
    f = compute_features(toy_grid([1, 2, 3, 4, 5, 6]), CFG)
    assert f.loc[3, "DO_mean4"] == np.mean([1, 2, 3, 4])      # window [t-3..t]
    assert f.loc[3, "DO_min2"] == 3 and f.loc[3, "DO_max2"] == 4
    assert np.isclose(f.loc[3, "DO_std2"], 0.5)               # std of [3,4], ddof=0


def test_slope_of_linear_ramp_is_exact_per_hour():
    f = compute_features(toy_grid([10, 11, 12, 13, 14, 15]), CFG)    # +1 per 15 min = +4 per hour
    assert np.isclose(f.loc[5, "DO_slope4"], 4.0)


def test_missing_values_age_and_valid_fraction():
    f = compute_features(toy_grid([5, np.nan, np.nan, 7, np.nan]), CFG)
    assert f.loc[3, "DO_age"] == 0 and f.loc[2, "DO_age"] == 2 and f.loc[4, "DO_age"] == 1
    assert f.loc[4, "DO_valid_frac4"] == 1 / 4                # only the 7 in the last 4 slots (idx 1..4)
    assert np.isnan(f.loc[2, "DO_lag1"]) and f.loc[2, "DO_age"] == 2


def test_absent_rows_are_not_filled_and_presence_features():
    g = toy_grid([5, np.nan, 7], present=[True, False, True])
    f = compute_features(g, CFG)
    assert f.loc[2, "steps_since_prev_row"] == 2 and f.loc[2, "present_frac4"] == 2 / 4


def test_prefix_invariance_no_future_dependence():
    rng = np.random.RandomState(0)
    do = rng.uniform(2, 12, 60)
    do[[7, 8, 20, 33]] = np.nan
    g = toy_grid(do)
    full = compute_features(g, CFG)
    for k in (10, 25, 40, 59):
        pre = compute_features(g.iloc[: k + 1].reset_index(drop=True), CFG).iloc[-1]
        a, b = pre.to_numpy(dtype=float), full.iloc[k].to_numpy(dtype=float)
        assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], atol=1e-9)


def test_changing_future_values_does_not_change_current_features():
    a = np.arange(1.0, 31.0)
    b = a.copy()
    b[20:] = 999.0                                           # alter everything after index 19
    fa, fb = compute_features(toy_grid(a), CFG), compute_features(toy_grid(b), CFG)
    pd.testing.assert_frame_equal(fa.iloc[:20], fb.iloc[:20])


def test_targets_are_future_valid_observations_or_nan():
    g = toy_grid([1, 2, np.nan, 4, 5, 6])
    y = make_targets(g, CFG)
    assert y.loc[0, "y_DO_h1"] == 2 and y.loc[0, "y_DO_h2"] != y.loc[0, "y_DO_h2"]   # t+2 is missing -> NaN
    assert y.loc[1, "y_DO_h2"] == 4
    assert y.loc[0, "ts_target_h2"] == g.loc[2, "ts"]


def test_dictionary_matches_built_columns():
    f = compute_features(toy_grid(np.arange(1.0, 20.0)), CFG)
    assert {s["name"] for s in feature_specs(CFG)} == set(f.columns)
