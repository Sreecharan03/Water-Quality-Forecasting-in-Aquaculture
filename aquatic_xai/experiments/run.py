"""One experiment task = one (regime, target variable, horizon): fit all models on the regime's training rows,
evaluate on its evaluation rows. Row-level absolute errors are kept for blocked-bootstrap analysis."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from aquatic_xai.models.baselines import persistence, seasonal_naive
from aquatic_xai.models.tabular import feature_columns, fit_predict
from aquatic_xai.splits.manifest import regime_masks, regimes

MODEL_NAMES = ["persistence", "seasonal_naive", "ridge_blind", "ridge_aware",
               "lgbm_blind", "lgbm_aware", "xgb_blind", "xgb_aware"]
ALGOS = {"ridge": "ridge", "lgbm": "lightgbm", "xgb": "xgboost"}


def find_regime(info: dict, k: int, name: str) -> dict:
    for r in regimes(info, k):
        if r["name"] == name:
            return r
    raise KeyError(name)


def run_task(T: pd.DataFrame, info: dict, cv_folds: int, regime_name: str, var: str, h: int,
             specs: list[dict], mcfg: dict, low_q: float) -> tuple[list[dict], pd.DataFrame]:
    """T = feature table joined with split assignments (columns role, fold, block_day)."""
    t0 = time.time()
    regime = find_regime(info, cv_folds, regime_name)
    tr_mask, ev_mask = regime_masks(T, info, regime)
    ycol, ccol = f"y_{var}_h{h}", f"{var}_cur"
    ok = ~T["is_warmup"] & T[ycol].notna()
    train = T[tr_mask & ok]
    ev = T[ev_mask & ok & T[ccol].notna()]          # common evaluation rows: valid target AND valid current reading
    y = ev[ycol].to_numpy(dtype=float)

    preds: dict[str, np.ndarray] = {"persistence": persistence(ev, var),
                                    "seasonal_naive": seasonal_naive(T, ev, var, h, mcfg["seasonal_steps"])}
    seed_mae: dict[str, list[float]] = {}
    for algo_key, algo in ALGOS.items():
        seeds = [0] if algo_key == "ridge" else mcfg["seeds"]
        for aware in (False, True):
            name = f"{algo_key}_{'aware' if aware else 'blind'}"
            cols = feature_columns(specs, aware)
            Xtr, Xev = train[cols].to_numpy(dtype=float), ev[cols].to_numpy(dtype=float)
            per_seed = [fit_predict(algo, mcfg[algo], s, Xtr, train[ycol].to_numpy(dtype=float), Xev) for s in seeds]
            seed_mae[name] = [float(np.mean(np.abs(p - y))) for p in per_seed]
            preds[name] = np.mean(np.abs(np.stack(per_seed) - y), axis=0)    # row-level abs error, seed-averaged
    ae = {k: (np.abs(v - y) if k in ("persistence", "seasonal_naive") else v) for k, v in preds.items()}

    out = ev[["pond", "grid_idx", "block_day", "ts_ist"]].copy()
    out["y"], out["cur"] = y, ev[ccol].to_numpy(dtype=float)
    out["y_train_low"] = float(np.quantile(train[ycol], low_q))
    for k, v in ae.items():
        out[f"ae_{k}"] = v
    metrics = []
    for k, v in ae.items():
        m = ~np.isnan(v)
        metrics.append({"regime": regime_name, "var": var, "h": h, "model": k, "n_eval": int(m.sum()),
                        "mae": float(np.mean(v[m])) if m.any() else None,
                        "seed_mae": seed_mae.get(k), "n_train": int(len(train)), "n_features": len(feature_columns(specs, k.endswith("aware")))
                        if k.startswith(("ridge", "lgbm", "xgb")) else None})
    trp = train[train[ccol].notna()]
    metrics.append({"regime": regime_name, "var": var, "h": h, "model": "_task", "seconds": round(time.time() - t0, 2),
                    "n_train": int(len(train)), "n_eval": int(len(ev)),
                    "mase_scale": float(np.mean(np.abs(trp[ycol].to_numpy(dtype=float) - trp[ccol].to_numpy(dtype=float))))})
    return metrics, out
