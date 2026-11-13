"""Leakage and alignment checks that run on the real feature tables (on Modal).

1. prefix_invariance: features recomputed from history truncated at t must equal the stored row.
   If any feature touched the future, truncating the future would change it.
2. target_alignment: targets re-derived by an independent timestamp lookup (not the grid shift).
3. identity_check: no feature column may equal a target column.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.features.build import compute_features


def sample_origins(table: pd.DataFrame, n: int, seed: int) -> np.ndarray:
    ok = table.index[~table["is_warmup"]].to_numpy()
    rng = np.random.RandomState(seed)
    return np.sort(rng.choice(ok, size=min(n, len(ok)), replace=False))


def prefix_invariance(grid: pd.DataFrame, table: pd.DataFrame, cfg: dict, rows: np.ndarray, nominal: int) -> dict:
    feat_cols = [c for c in table.columns if c in compute_features(grid.iloc[:60].reset_index(drop=True), cfg, nominal).columns]
    max_diff, bad = 0.0, 0
    for r in rows:
        g = int(table.loc[r, "grid_idx"])
        prefix = compute_features(grid.iloc[: g + 1].reset_index(drop=True), cfg, nominal).iloc[-1]
        full = table.loc[r, feat_cols].astype(float)
        a, b = prefix[feat_cols].astype(float).to_numpy(), full.to_numpy()
        same_nan = np.array_equal(np.isnan(a), np.isnan(b))
        d = float(np.nanmax(np.abs(a - b))) if np.isfinite(a).any() else 0.0
        max_diff = max(max_diff, d)
        if not same_nan or d > 1e-9:
            bad += 1
    return {"origins_checked": int(len(rows)), "features_checked": len(feat_cols), "mismatching_origins": bad,
            "max_abs_diff": max_diff}


def target_alignment(proc: pd.DataFrame, table: pd.DataFrame, cfg: dict, rows: np.ndarray, nominal: int, tol: int) -> dict:
    """Independent re-derivation: nearest processed row within tol minutes of t + h."""
    ts = proc["ts_ist"].to_numpy()
    checked, bad = 0, 0
    for r in rows:
        t = table.loc[r, "ts_ist"]
        for h in cfg["horizons"]:
            want = np.datetime64(t + pd.Timedelta(minutes=nominal * h))
            j = int(np.searchsorted(ts, want))
            cands = [k for k in (j - 1, j) if 0 <= k < len(ts) and abs((ts[k] - want) / np.timedelta64(1, "m")) <= tol]
            for v in cfg["variables"]:
                exp = np.nan
                if cands:
                    k = min(cands, key=lambda c: abs(ts[c] - want))
                    exp = proc[v].iloc[k]
                got = table.loc[r, f"y_{v}_h{h}"]
                checked += 1
                if not ((np.isnan(exp) and np.isnan(got)) or (exp == got)):
                    bad += 1
    return {"target_values_checked": checked, "mismatches": bad}


def identity_check(table: pd.DataFrame, cfg: dict) -> dict:
    feats = [c for c in table.columns if not c.startswith(("y_", "ts_target", "pond", "grid_idx", "ts_ist", "is_warmup"))]
    worst = ("", "", 0.0)
    for tcol in [c for c in table.columns if c.startswith("y_")]:
        t = table[tcol]
        m = t.notna()
        for f in feats:
            eq = float((table.loc[m, f] == t[m]).mean()) if m.any() else 0.0
            if eq > worst[2]:
                worst = (f, tcol, eq)
    return {"max_equal_fraction": round(worst[2], 4), "feature": worst[0], "target": worst[1]}
