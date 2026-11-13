"""Toy-fixture tests for the split design (synthetic, unit-test only; never research data)."""
import numpy as np
import pandas as pd
import pytest

from aquatic_xai.splits.grouped import assign_folds, pick_sealed
from aquatic_xai.splits.manifest import (build_assignments, check_assignments, content_hash, regime_masks, regimes,
                                         split_version)
from aquatic_xai.splits.temporal import choose_cutoffs, window_labels

CFG = {"nominal_interval_min": 15, "embargo_steps": 48, "max_lookback_steps": 24, "max_horizon_steps": 24,
       "fractions": {"train": 0.5, "val": 0.25}, "n_sealed_ponds": 1, "seed": 7, "cv_folds": 2,
       "min_val_origins": 50, "min_test_origins": 50, "usable_requires": ["y_DO_h24", "y_pH_h24", "y_Temp_h24"]}


def toy_table(spans):
    parts = []
    for pond, n_days in spans.items():
        ts = pd.Timestamp("2026-01-01") + pd.to_timedelta(np.arange(n_days * 96) * 15, unit="m")
        df = pd.DataFrame({"pond": pond, "grid_idx": np.arange(n_days * 96), "ts_ist": ts})
        df["is_warmup"] = df["grid_idx"] < 24
        df["ts_target_h24"] = df["ts_ist"] + pd.Timedelta(hours=6)
        for v in ("DO", "pH", "Temp"):
            df[f"y_{v}_h24"] = 1.0
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


SPANS = {"A": 12, "B": 12, "C": 12, "D": 5, "E": 12}      # D stops early: no validation/test coverage


def test_windows_respect_embargo_exactly():
    ts = pd.Series(pd.date_range("2026-01-01", periods=96 * 12, freq="15min"))
    t1, t2 = pd.Timestamp("2026-01-05"), pd.Timestamp("2026-01-09")
    lab = window_labels(ts, t1, t2, pd.Timedelta(hours=12))
    s = pd.Series(lab)
    assert (ts[s == "train"].max() <= t1) and (ts[s == "val"].min() > t1 + pd.Timedelta(hours=12))
    # no train target window (t+6h) reaches into a validation feature window (t-6h)
    assert ts[s == "train"].max() + pd.Timedelta(hours=6) <= ts[s == "val"].min() - pd.Timedelta(hours=6)
    assert ts[s == "val"].max() + pd.Timedelta(hours=6) <= ts[s == "test"].min() - pd.Timedelta(hours=6)
    assert set(lab) == {"train", "embargo_train_val", "val", "embargo_val_test", "test"}


def test_cutoffs_are_calendar_midnights_and_increasing():
    t = toy_table(SPANS)
    t1, t2 = choose_cutoffs(t["ts_ist"], CFG["fractions"])
    assert t1 == t1.normalize() and t2 == t2.normalize() and t1 < t2


def test_assignments_are_deterministic_and_sealed_ponds_isolated():
    t = toy_table(SPANS)
    a1, info1 = build_assignments(t, CFG)
    a2, info2 = build_assignments(t, CFG)
    assert content_hash(a1) == content_hash(a2) and info1 == info2
    assert len(info1["sealed_ponds"]) == 1 and "D" not in info1["sealed_ponds"]    # D has no test coverage
    s = info1["sealed_ponds"][0]
    assert not a1.loc[a1["pond"] == s, "role"].isin(["dev_train", "dev_val", "seen_pond_test"]).any()
    assert a1.loc[a1["pond"] == "D", "fold"].eq(-1).all()                          # train-only pond
    chk = check_assignments(a1, info1, CFG)
    assert chk["all_pass"] and chk["embargo_ok"] and chk["sealed_rows_in_dev_roles"] == 0


def test_unseen_regimes_have_disjoint_ponds_and_future_eval():
    t = toy_table(SPANS)
    a, info = build_assignments(t, CFG)
    for r in regimes(info, CFG["cv_folds"]):
        tr, ev = regime_masks(a, info, r)
        assert not (tr & ev).any()
        if r["kind"] == "future_unseen" or r["name"] == "FINAL_unseen_ponds_future":
            assert not set(a.loc[tr, "pond"]) & set(a.loc[ev, "pond"])
        if r["kind"] in ("future_seen", "future_unseen", "final"):
            assert a.loc[ev, "ts_ist"].min() > a.loc[tr, "ts_ist"].max()
        assert not set(info["sealed_ponds"]) & set(a.loc[tr, "pond"])


def test_checker_catches_a_leaky_assignment():
    t = toy_table(SPANS)
    a, info = build_assignments(t, CFG)
    s = info["sealed_ponds"][0]
    bad = a.copy()
    idx = bad.index[(bad["pond"] == s) & (bad["window"] == "train") & (~bad["is_warmup"])][:10]
    bad.loc[idx, "role"] = "dev_train"                                              # sealed pond leaks into training
    assert not check_assignments(bad, info, CFG)["all_pass"]


def test_folds_balanced_deterministic_and_small_ponds_never_held_out():
    counts = {"a": 400, "b": 380, "c": 300, "d": 290, "e": 100, "f": 10}
    f1, f2 = assign_folds(counts, 2, 50), assign_folds(counts, 2, 50)
    assert f1 == f2 and f1["f"] == -1
    load = [sum(counts[p] for p, v in f1.items() if v == k) for k in (0, 1)]
    assert abs(load[0] - load[1]) <= 100


def test_not_enough_eligible_ponds_raises_and_version_changes_with_config():
    with pytest.raises(ValueError):
        pick_sealed(["a", "b"], 3, 1)
    assert split_version("ft-x", CFG) != split_version("ft-x", {**CFG, "seed": 8})
