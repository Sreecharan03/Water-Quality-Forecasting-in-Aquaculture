"""Toy tests for the Phase 1b-R adapter and the generalised grid code (synthetic; unit-test only)."""
import numpy as np
import pandas as pd

from aquatic_xai.data.external import do_mg_per_l, prepare_pond, to_grid
from aquatic_xai.features.build import compute_features, make_targets
from aquatic_xai.features.daily import daily_features, prefix_invariance_daily
from aquatic_xai.alerts.labels import window_labels

FCFG = {"variables": ["DO", "pH", "Temp"], "lags": [1, 2, 3, 4, 6, 12], "windows": [2, 6, 12], "slope_window": 6, "age_cap": 48,
        "flag_lookback": 12, "warmup_steps": 12, "horizons": [1, 2, 12]}


def _raw(n_days=6, hole=None):
    t = pd.date_range("2023-06-01 00:00", periods=n_days * 144, freq="10min", tz="UTC")
    rng = np.random.RandomState(0)
    df = pd.DataFrame({"datetime_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "DO_mgL": 6 + np.sin(np.arange(len(t)) / 23) + rng.normal(0, .1, len(t)),
                       "pH": 7.8 + rng.normal(0, .02, len(t)), "temperature": 20 + rng.normal(0, .1, len(t))})
    if hole is not None:
        df.loc[hole, "DO_mgL"] = np.nan
    return df


def test_oxygen_conversion_known_value():
    mg = do_mg_per_l(pd.Series([312.5]), pd.Series([30.0]))             # about 10.2 mg/L at salinity 30
    assert abs(mg.iloc[0] - 312.5 * 31.998 * 1.024 / 1000) < 1e-9 and 10.0 < mg.iloc[0] < 10.5


def test_grid_uses_only_exact_half_hour_timestamps_and_never_interpolates():
    raw = _raw(hole=slice(30, 36))                                      # 10-minute readings 30..36 missing (.loc includes both ends)
    pond = prepare_pond(raw)
    g = to_grid(pond)
    assert len(g) == (6 * 144 - 1) // 3 + 1 and g["present"].all()
    src = pond.set_index("t")["DO"]
    assert np.allclose(g["DO"].dropna().to_numpy(), src.reindex(pd.to_datetime(g.loc[g["DO"].notna(), "utc"], utc=True)).to_numpy())
    assert g["DO"].isna().sum() == 3                                    # only the on-grid readings 30, 33, 36 are missing; nothing is filled


def test_grid_time_is_fixed_standard_time_and_local_hour_follows_new_york():
    g = to_grid(prepare_pond(_raw()))
    assert (g["utc"] - g["ts"]).eq(pd.Timedelta(hours=5)).all()          # EST = UTC-5, never changes
    assert g["ny_hour"].iloc[0] == 20.0                                  # 2023-06-01 00:00 UTC = 20:00 EDT the day before


def test_features_and_targets_on_the_30_minute_grid_are_causal():
    g = to_grid(prepare_pond(_raw()))
    f, t = compute_features(g, FCFG, nominal=30), make_targets(g, FCFG, nominal=30)
    assert f["DO_cur"].equals(g["DO"]) and f["DO_lag2"].iloc[10] == g["DO"].iloc[8]
    assert t["y_DO_h12"].iloc[5] == g["DO"].iloc[17]                     # 6 h ahead = 12 steps
    cut = 100
    f2 = compute_features(g.iloc[: cut + 1].reset_index(drop=True), FCFG, nominal=30)
    assert np.allclose(f2.iloc[-1].astype(float), f.iloc[cut].astype(float), equal_nan=True)   # prefix invariance


def test_daily_features_with_a_48_step_day():
    g = to_grid(prepare_pond(_raw(n_days=8)))
    tab = pd.DataFrame({"grid_idx": np.arange(len(g)), "DO_cur": g["DO"], "pH_cur": g["pH"], "Temp_cur": g["Temp"]})
    d = daily_features(tab, [1, 2, 12], day=48)
    assert d["DO_d1"].iloc[100] == g["DO"].iloc[52] and d["DO_yday_tgt_h12"].iloc[100] == g["DO"].iloc[64]   # 100+12-48
    res = prefix_invariance_daily(tab, [1, 2, 12], np.arange(60, 180, 13), day=48)
    assert res["mismatching_origins"] == 0


def test_alert_labels_with_a_48_step_day():
    d = pd.DataFrame({"grid_idx": np.arange(200), "DO_cur": np.full(200, 6.0)})
    d.loc[100:101, "DO_cur"] = 1.0
    lab, yd = window_labels(d, 12, 2.0, day=48)
    assert np.where(lab == 1)[0].min() == 88 and np.where(yd == 1.0)[0].min() == 136   # dip visible exactly 48 slots later
