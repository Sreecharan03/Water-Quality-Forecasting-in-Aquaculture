"""Causal feature construction on the 15-minute grid.

Every feature at origin index g is a function of grid points <= g only:
- lags use shift(+k); rolling windows are trailing and include g;
- no backward fill, no centred windows, no statistics fitted on future rows.
Targets use shift(-h) and are real, valid observations or NaN (never interpolated).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from aquatic_xai.data.clean import VAR_FLAG_COLS
from aquatic_xai.data.treatments import grid_index

FEATURE_CODE_VERSION = "feat-v1"
FLAG_SOURCE_COLS = ["flag_do_lt01", "flag_do_jump", "flag_do_gt10_am", "flag_ph_range", "flag_ph_jump", "flag_gap"]


def feature_version(dataset_version: str, cfg: dict) -> str:
    payload = json.dumps({"data": dataset_version, "cfg": cfg, "code": FEATURE_CODE_VERSION}, sort_keys=True)
    return "ft-" + hashlib.sha256(payload.encode()).hexdigest()[:12]


def make_grid(proc: pd.DataFrame, nominal: int, tol: int) -> tuple[pd.DataFrame, int]:
    """Place processed rows on the nominal grid. Returns (grid, n_rows_not_placed)."""
    t0, g, ok = grid_index(proc["ts_ist"], nominal, tol)
    n = int(g.max()) + 1
    first = np.full(n, -1)
    for i in np.where(ok)[0]:
        if first[g[i]] == -1:
            first[g[i]] = i
    present = first >= 0
    take = np.where(present, first, 0)
    grid = pd.DataFrame({"present": present})
    grid["ts"] = t0 + pd.to_timedelta(np.arange(n) * nominal, unit="m")
    for v in ("DO", "pH", "Temp"):
        grid[v] = np.where(present, proc[v].to_numpy()[take], np.nan)
    for c in FLAG_SOURCE_COLS:
        grid[c] = np.where(present, proc[c].to_numpy()[take], False)
    return grid, int(len(proc) - present.sum())


def _since_last(flag: np.ndarray, idx: np.ndarray, cap: int, shift: int = 0) -> np.ndarray:
    last = pd.Series(np.where(flag, idx, np.nan)).ffill()
    if shift:
        last = last.shift(shift)
    age = idx - last.to_numpy()
    return np.where(np.isnan(age), cap, np.minimum(age, cap))


def compute_features(grid: pd.DataFrame, cfg: dict, nominal: int = 15) -> pd.DataFrame:
    n = len(grid)
    idx = np.arange(n, dtype=float)
    t = pd.Series(idx, index=grid.index)
    L, cap, w_s = cfg["flag_lookback"], cfg["age_cap"], cfg["slope_window"]
    F: dict[str, pd.Series] = {}

    for v in cfg["variables"]:
        x = grid[v]
        valid = x.notna()
        m = valid.astype(float)
        F[f"{v}_cur"] = x
        for k in cfg["lags"]:
            F[f"{v}_lag{k}"] = x.shift(k)
        for w in cfg["windows"]:
            r = x.rolling(w, min_periods=1)
            F[f"{v}_mean{w}"], F[f"{v}_min{w}"], F[f"{v}_max{w}"] = r.mean(), r.min(), r.max()
            F[f"{v}_std{w}"] = x.rolling(w, min_periods=2).std(ddof=0)
        y = x.fillna(0.0)

        def rs(a: pd.Series) -> pd.Series:
            return a.rolling(w_s, min_periods=1).sum()

        Sn, St, Sy, Sty, Stt = rs(m), rs(m * t), rs(m * y), rs(m * t * y), rs(m * t * t)
        den = Sn * Stt - St ** 2
        F[f"{v}_slope{w_s}"] = ((Sn * Sty - St * Sy) / den * (60.0 / nominal)).where((Sn >= 3) & (den > 0.5))
        F[f"{v}_age"] = pd.Series(_since_last(valid.to_numpy(), idx, cap), index=grid.index)
        F[f"{v}_valid_frac{L}"] = m.rolling(L, min_periods=1).sum() / L

    do_any = grid[VAR_FLAG_COLS["DO"]].any(axis=1).astype(float)
    ph_any = grid[VAR_FLAG_COLS["pH"]].any(axis=1).astype(float)
    gap = grid["flag_gap"].astype(float)
    F["flag_do_now"], F["flag_ph_now"], F["flag_gap_now"] = do_any, ph_any, gap
    F[f"n_flag_do_{L}"] = do_any.rolling(L, min_periods=1).sum()
    F[f"n_flag_ph_{L}"] = ph_any.rolling(L, min_periods=1).sum()
    F[f"n_flag_gap_{L}"] = gap.rolling(L, min_periods=1).sum()
    pres = grid["present"].astype(float)
    F[f"present_frac{L}"] = pres.rolling(L, min_periods=1).sum() / L
    F["steps_since_prev_row"] = pd.Series(_since_last(grid["present"].to_numpy(), idx, cap, shift=1), index=grid.index)
    hour = grid["ts"].dt.hour + grid["ts"].dt.minute / 60.0
    F["hour_sin"], F["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    return pd.DataFrame(F)


def make_targets(grid: pd.DataFrame, cfg: dict, nominal: int = 15) -> pd.DataFrame:
    T: dict[str, pd.Series] = {}
    for h in cfg["horizons"]:
        T[f"ts_target_h{h}"] = grid["ts"] + pd.Timedelta(minutes=nominal * h)
        for v in cfg["variables"]:
            T[f"y_{v}_h{h}"] = grid[v].shift(-h)
    return pd.DataFrame(T)


def build_pond_table(proc: pd.DataFrame, rules: dict, cfg: dict, pond: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    nominal, tol = rules["grid"]["nominal_interval_min"], rules["grid"]["grid_tolerance_min"]
    grid, not_placed = make_grid(proc, nominal, tol)
    feats = compute_features(grid, cfg, nominal)
    targets = make_targets(grid, cfg, nominal)
    meta = pd.DataFrame({"pond": pond, "grid_idx": np.arange(len(grid)), "ts_ist": grid["ts"],
                         "is_warmup": np.arange(len(grid)) < cfg["warmup_steps"]})
    table = pd.concat([meta, feats, targets], axis=1)[grid["present"].to_numpy()].reset_index(drop=True)
    return table, grid, not_placed
