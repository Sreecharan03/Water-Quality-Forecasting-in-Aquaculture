"""Toy tests for Phase 6 labels, conformal ranges, alert metrics (synthetic; unit-test only)."""
import numpy as np
import pandas as pd

from aquatic_xai.alerts.evaluate import ap_ci, episode_stats
from aquatic_xai.alerts.labels import episode_onsets, window_labels
from aquatic_xai.uncertainty.conformal import conformal_q


def _pond():
    d = pd.DataFrame({"grid_idx": np.arange(300), "DO_cur": np.full(300, 6.0)})
    d.loc[150:152, "DO_cur"] = 2.0
    return d


def test_window_label_marks_exactly_the_origins_before_the_dip():
    lab, yday = window_labels(_pond(), 12, 3.0)
    assert np.where(lab == 1)[0].tolist() == list(range(138, 152))        # window (g, g+12] reaches slots 150..152
    assert lab[100] == 0 and lab[290] != 1
    assert np.where(yday == 2.0)[0].min() == 234                           # the earlier dip becomes visible 96 slots later, never before


def test_label_is_unknown_when_window_mostly_missing():
    d = _pond()
    d = d[~d["grid_idx"].between(200, 215)].reset_index(drop=True)
    lab, _ = window_labels(d, 12, 3.0)
    i = d.index[d["grid_idx"] == 195][0]
    assert np.isnan(lab[i])                                                # next 12 slots mostly absent and no event seen


def test_yesterday_window_feature_ignores_the_future():
    d = _pond()
    _, y1 = window_labels(d, 12, 3.0)
    d2 = d.copy()
    d2.loc[d2["grid_idx"] > 240, "DO_cur"] = 0.1
    _, y2 = window_labels(d2, 12, 3.0)
    assert np.array_equal(y1[:240], y2[:240], equal_nan=True)              # origins <= 239 use only slots <= 167


def test_episode_onset():
    assert episode_onsets(_pond(), 3.0).tolist() == [150]


def test_conformal_range_covers_about_the_target_share():
    rng = np.random.RandomState(0)
    cal, test = np.abs(rng.normal(size=5000)), np.abs(rng.normal(size=20000))
    q = conformal_q(cal, 0.1)
    assert abs((test <= q).mean() - 0.9) < 0.015
    assert np.isinf(conformal_q(np.array([1.0, 2.0]), 0.01))


def test_ap_ci_prefers_the_informative_score():
    rng = np.random.RandomState(1)
    n = 600
    y = rng.binomial(1, 0.3, n)
    d = pd.DataFrame({"pond": ["A"] * n, "block_day": [f"d{i % 20}" for i in range(n)], "y": y,
                      "good": y + rng.normal(0, 0.5, n), "bad": rng.normal(size=n)})
    r = ap_ci(d, "y", ["good", "bad"], B=100, seed=2, level=99)
    assert r["diff"]["bad"][0] > 0.2 and r["diff"]["bad"][1] > 0


def test_episode_stats_counts_catches_and_false_alarms():
    rows = pd.DataFrame({"pond": "A", "grid_idx": np.arange(100), "block_day": "d0", "y": 0.0, "s": 0.0})
    rows.loc[rows["grid_idx"].between(40, 60), "y"] = 1.0
    rows.loc[rows["grid_idx"] == 45, "s"] = 1.0                            # alert 5 slots (1.25 h) before an onset at 50
    rows.loc[rows["grid_idx"] == 10, "s"] = 1.0                            # a false alarm
    st = episode_stats(rows, {"A": [50]}, "s", 0.5, 4, 24)
    assert st["episodes"] == 1 and st["caught"] == 1 and st["median_lead_h"] == 1.25 and st["false_alarm_pond_days"] == 1
