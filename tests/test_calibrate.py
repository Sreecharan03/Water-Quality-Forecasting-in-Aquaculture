"""Toy tests for Phase 6b calibration and level selection (synthetic; unit-test only)."""
import numpy as np
import pandas as pd

from aquatic_xai.alerts.calibrate import brier, choose_level, evaluate_level, false_alarm_flags, fit_isotonic


def test_isotonic_is_monotone_and_improves_brier_on_miscalibrated_scores():
    rng = np.random.RandomState(0)
    true_p = rng.uniform(0, 1, 4000)
    y = rng.binomial(1, true_p)
    raw = np.clip(true_p ** 3, 0, 1)                       # systematically too low
    iso = fit_isotonic(raw[:2000], y[:2000])
    cal = iso.predict(raw[2000:])
    assert brier(cal, y[2000:]) < brier(raw[2000:], y[2000:])
    grid = np.linspace(0, 1, 50)
    assert (np.diff(iso.predict(grid)) >= 0).all()          # ranking is never reversed


def test_level_is_chosen_on_calibration_rows_and_applied_unchanged():
    def rows(seed):
        r = np.random.RandomState(seed)
        d = pd.DataFrame({"pond": "A", "grid_idx": np.arange(300), "block_day": [f"d{i // 100}" for i in range(300)], "y": 0.0})
        d.loc[d["grid_idx"].between(190, 215), "y"] = 1.0
        d["s"] = r.uniform(0, 0.3, 300)
        d.loc[d["grid_idx"].between(170, 180), "s"] = 0.9      # a warning 5-7 h... before the onset at 200
        return d
    cal, test = rows(1), rows(2)
    t, st = choose_level(cal, {"A": [200]}, "s", 0.8, 4, 24)
    assert st["recall"] >= 0.8 and 0.3 < t <= 0.9
    ev = evaluate_level(test, {"A": [200]}, "s", t, 4, 24)
    assert ev["caught"] == 1


def test_false_alarm_flags_are_per_pond_day():
    d = pd.DataFrame({"pond": "A", "block_day": ["d0", "d0", "d1"], "y": [0.0, 0.0, 1.0], "s": [0.9, 0.1, 0.9]})
    f = false_alarm_flags(d, "s", 0.5)
    assert f.set_index("block_day")["fa"].to_dict() == {"d0": 1.0, "d1": 0.0}   # an alert during a real event is not a false alarm
