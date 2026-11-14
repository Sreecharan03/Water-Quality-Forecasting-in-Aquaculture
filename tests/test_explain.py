"""Toy tests for Phase 7/8 helpers (synthetic; unit-test only). LightGBM-dependent tests are skipped where it is not installed."""
import numpy as np
import pytest

from aquatic_xai.explain.shap_utils import deletion_losses, family_map, family_of, family_shares, mean_abs, safe_spearman, top_k


def test_family_mapping_and_shares_sum_to_one():
    specs = [{"name": "DO_cur", "group": "history"}, {"name": "DO_mean4", "group": "rolling"}, {"name": "hour_sin", "group": "time"}]
    fm = family_map(specs, ["DO_d1"])
    assert family_of("DO_d1", fm) == "daily" and family_of("ydaymin_W24", fm) == "daily" and family_of("anchor_gap", fm) == "anchor_gap"
    sh = family_shares(np.array([2.0, 1.0, 0.5, 0.5]), ["DO_cur", "DO_mean4", "hour_sin", "DO_d1"], fm)
    assert abs(sum(sh.values()) - 1.0) < 1e-12 and sh["history"] == 0.5


def test_spearman_and_topk():
    assert safe_spearman(np.array([1.0, 2.0, 3.0]), np.array([10.0, 20.0, 30.0])) == pytest.approx(1.0)
    assert np.isnan(safe_spearman(np.ones(3), np.array([1.0, 2.0, 3.0])))
    assert top_k(np.array([0.1, 0.9, 0.5]), 2) == [1, 2]


def test_shap_contributions_add_up_to_the_prediction():
    lgb = pytest.importorskip("lightgbm")
    from aquatic_xai.explain.shap_utils import shap_contrib
    rng = np.random.RandomState(0)
    X = rng.normal(size=(400, 4))
    y = 3 * X[:, 0] - X[:, 1] + rng.normal(0, 0.1, 400)
    m = lgb.LGBMRegressor(n_estimators=30, num_leaves=7, min_child_samples=5, verbose=-1, random_state=0).fit(X, y)
    full = m.booster_.predict(X, pred_contrib=True)
    assert np.allclose(full.sum(axis=1), m.predict(X), atol=1e-6)               # local accuracy property of SHAP
    c = shap_contrib(m, X)
    assert c.shape == (400, 4) and np.argmax(mean_abs(c)) == 0                  # the feature that matters most gets the largest attribution


def test_deletion_control_punishes_removing_important_features_more_than_random_ones():
    lgb = pytest.importorskip("lightgbm")
    rng = np.random.RandomState(1)
    X = rng.normal(size=(600, 10))
    y = 4 * X[:, 0] + rng.normal(0, 0.1, 600)
    m = lgb.LGBMRegressor(n_estimators=60, num_leaves=7, min_child_samples=5, verbose=-1, random_state=0).fit(X, y)
    loss = lambda Z: np.abs(m.predict(Z) - y)
    full, top, rand = deletion_losses(loss, X, np.median(X, axis=0), [0, 1, 2], 3, 30, 5)
    assert top.mean() > rand.mean() > full.mean()
