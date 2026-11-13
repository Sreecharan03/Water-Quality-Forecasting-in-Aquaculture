"""Toy-fixture tests for baselines, feature sets, bootstrap and train-only fitting (synthetic; unit-test only)."""
import numpy as np
import pandas as pd

from aquatic_xai.experiments.evaluate import diff_ci, improvement_ci, mean_ci
from aquatic_xai.features.dictionary import feature_specs
from aquatic_xai.models.baselines import persistence, seasonal_naive
from aquatic_xai.models.tabular import feature_columns, fit_predict, make_model

FCFG = {"variables": ["DO", "pH", "Temp"], "lags": [1, 2, 4], "windows": [2, 4], "slope_window": 4,
        "age_cap": 10, "flag_lookback": 4, "warmup_steps": 4, "horizons": [1, 2]}


def test_persistence_and_seasonal_naive_use_only_past_values():
    full = pd.DataFrame({"pond": "A", "grid_idx": np.arange(200), "DO_cur": np.arange(200, dtype=float)})
    rows = full[full["grid_idx"].isin([150, 50])]
    assert persistence(rows, "DO").tolist() == [50.0, 150.0]
    s = seasonal_naive(full, rows, "DO", h=4, steps_per_day=96)
    assert s[1] == 58.0 and np.isnan(s[0])                    # 150+4-96 = 58; 50+4-96 < 0 -> unavailable
    assert (rows["grid_idx"].to_numpy() + 4 - 96 <= rows["grid_idx"].to_numpy()).all()   # never in the future


def test_seasonal_naive_returns_nan_for_missing_reference_row():
    full = pd.DataFrame({"pond": "A", "grid_idx": [0, 1, 2, 100], "DO_cur": [1.0, 2.0, 3.0, 4.0]})
    s = seasonal_naive(full, full[full["grid_idx"] == 100], "DO", h=4, steps_per_day=96)   # needs idx 8: absent
    assert np.isnan(s[0])


def test_blind_and_aware_differ_only_by_quality_group():
    specs = feature_specs(FCFG)
    blind, aware = feature_columns(specs, False), feature_columns(specs, True)
    quality = {s["name"] for s in specs if s["group"] == "quality"}
    assert set(aware) - set(blind) == quality and set(blind) < set(aware) and quality
    assert not set(blind) & quality


def test_ridge_imputer_and_scaler_are_fitted_on_training_rows_only():
    Xtr = np.array([[1.0, 10.0], [3.0, np.nan], [5.0, 30.0], [7.0, 50.0]])
    m = make_model("ridge", {"alpha": 1.0}, 0)
    m.fit(Xtr, np.array([1.0, 2.0, 3.0, 4.0]))
    assert np.allclose(m.steps[0][1].statistics_, np.nanmedian(Xtr, axis=0))
    before = m.predict(np.array([[4.0, np.nan]]))
    m.predict(np.array([[1000.0, 1000.0]]))                       # predicting on other data must not change the fit
    assert np.allclose(m.predict(np.array([[4.0, np.nan]])), before)


def test_lightgbm_same_seed_same_predictions():
    rng = np.random.RandomState(0)
    X, y = rng.normal(size=(300, 4)), rng.normal(size=300)
    params = {"n_estimators": 20, "learning_rate": 0.1, "num_leaves": 7, "min_child_samples": 5, "subsample": 0.8,
              "subsample_freq": 1, "colsample_bytree": 0.8, "deterministic": True, "force_row_wise": True}
    a = fit_predict("lightgbm", params, 3, X, y, X[:20])
    b = fit_predict("lightgbm", params, 3, X, y, X[:20])
    assert np.allclose(a, b)


def _df(values_a, values_b=None):
    n = len(values_a)
    d = pd.DataFrame({"pond": ["P"] * n, "block_day": [f"d{i % 10}" for i in range(n)], "a": values_a})
    if values_b is not None:
        d["b"] = values_b
    return d


def test_mean_ci_point_estimate_and_block_resampling():
    d = _df(np.arange(100, dtype=float))
    est, lo, hi, n = mean_ci(d, "a", B=500, seed=1)
    assert np.isclose(est, 49.5) and lo <= est <= hi and n == 100
    flat = mean_ci(_df(np.full(100, 2.0)), "a", B=200, seed=1)
    assert flat[0] == flat[1] == flat[2] == 2.0                    # no spread -> no interval


def test_improvement_and_diff_signs():
    base = np.full(100, 2.0)
    d = _df(base * 0.5, base)                                      # model errors are half the reference errors
    est, lo, hi, _ = improvement_ci(d, "a", "b", B=300, seed=2)
    assert np.isclose(est, 0.5) and lo > 0
    dif = diff_ci(d, "a", "b", B=300, seed=2)
    assert dif[0] < 0 and dif[2] < 0                               # negative = a better
