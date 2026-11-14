"""Toy tests for Phase 5b daily features and anchoring (synthetic; unit-test only)."""
import numpy as np
import pandas as pd

from aquatic_xai.features.daily import daily_features, prefix_invariance_daily
from aquatic_xai.models.anchored import add_anchor_gap, anchor_for
from aquatic_xai.models.baselines import seasonal_naive


def _pond(n=400, drop=()):
    g = np.array([i for i in range(n) if i not in drop])
    rng = np.random.RandomState(0)
    d = pd.DataFrame({"pond": "A", "grid_idx": g})
    for v in ("DO", "pH", "Temp"):
        d[f"{v}_cur"] = rng.normal(size=len(g)) + np.sin(2 * np.pi * g / 96)
    return d


def test_daily_features_use_expected_past_readings():
    d = _pond()
    f = daily_features(d, [1, 4, 24])
    r = d.index[d["grid_idx"] == 200][0]
    assert f.loc[r, "DO_d1"] == d.loc[d["grid_idx"] == 104, "DO_cur"].iloc[0]
    assert f.loc[r, "DO_yday_tgt_h24"] == d.loc[d["grid_idx"] == 128, "DO_cur"].iloc[0]      # 200+24-96
    win = d[(d["grid_idx"] > 104) & (d["grid_idx"] <= 200)]["pH_cur"]
    assert np.isclose(f.loc[r, "pH_dmean96"], win.mean()) and f.loc[r, "pH_dmax96"] == win.max()


def test_yday_target_feature_equals_seasonal_naive_baseline():
    d = _pond(drop=(150, 151))
    f = daily_features(d, [24])
    sn = seasonal_naive(d, d, "Temp", 24, 96)
    assert np.allclose(f["Temp_yday_tgt_h24"].to_numpy(), sn, equal_nan=True)


def test_daily_features_never_use_the_future():
    d = _pond(drop=(120, 300))
    rows = np.arange(100, 380, 17)
    res = prefix_invariance_daily(d, [1, 4, 24], rows)
    assert res["mismatching_origins"] == 0 and res["max_abs_diff"] == 0.0
    d2 = d.copy()
    d2.loc[d2["grid_idx"] > 250, ["DO_cur", "pH_cur", "Temp_cur"]] = 1e6        # corrupt the future of origin 250
    r = d.index[d["grid_idx"] == 250][0]
    cols = list(daily_features(d, [1, 4, 24]).columns)
    assert np.array_equal(daily_features(d, [1, 4, 24]).loc[r, cols].to_numpy(), daily_features(d2, [1, 4, 24]).loc[r, cols].to_numpy(), equal_nan=True)


def test_anchor_and_fallback():
    df = pd.DataFrame({"DO_cur": [5.0, 6.0, 7.0], "DO_yday_tgt_h24": [4.0, np.nan, 9.0]})
    a, fb = anchor_for(df, "DO", 24, "yesterday")
    assert a.tolist() == [4.0, 6.0, 9.0] and fb.tolist() == [False, True, False]
    a, fb = anchor_for(df, "DO", 4, "persistence")
    assert a.tolist() == [5.0, 6.0, 7.0] and not fb.any()
    assert add_anchor_gap(df, "DO", np.array([4.0, 6.0, 9.0])).tolist() == [-1.0, 0.0, 2.0]
