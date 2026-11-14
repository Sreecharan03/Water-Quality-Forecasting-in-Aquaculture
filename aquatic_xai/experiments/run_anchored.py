"""Phase 5b task: one (regime, target, horizon). Fits anchored-residual LightGBM (quality-blind and quality-aware)."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from aquatic_xai.experiments.run import find_regime
from aquatic_xai.models.anchored import add_anchor_gap, anchor_for, anchored_columns
from aquatic_xai.models.baselines import persistence, seasonal_naive
from aquatic_xai.models.tabular import fit_predict
from aquatic_xai.splits.manifest import regime_masks


def run_task_anchored(T: pd.DataFrame, info: dict, cv_folds: int, regime_name: str, var: str, h: int, base_specs: list[dict],
                      daily: list[dict], lgbm_params: dict, acfg: dict, seasonal_steps: int, low_q: float):
    t0 = time.time()
    regime = find_regime(info, cv_folds, regime_name)
    tr_mask, ev_mask = regime_masks(T, info, regime)
    ycol, ccol = f"y_{var}_h{h}", f"{var}_cur"
    kind = acfg["anchors"][h]
    ok = ~T["is_warmup"] & T[ycol].notna() & T[ccol].notna()     # anchoring needs a valid current reading in training too
    train, ev = T[tr_mask & ok], T[ev_mask & ok]
    y, ytr = ev[ycol].to_numpy(dtype=float), train[ycol].to_numpy(dtype=float)
    a_tr, fb_tr = anchor_for(train, var, h, kind)
    a_ev, fb = anchor_for(ev, var, h, kind)

    out = ev[["pond", "grid_idx", "block_day", "ts_ist"]].copy()
    out["y"], out["cur"], out["anchor"], out["fallback"] = y, ev[ccol].to_numpy(dtype=float), a_ev, fb
    out["y_train_low"] = float(np.quantile(ytr, low_q))
    out["ae_persistence"] = np.abs(persistence(ev, var) - y)
    out["ae_seasonal_naive"] = np.abs(seasonal_naive(T, ev, var, h, seasonal_steps) - y)
    metrics, seed_mae = [], {}
    for aware in (False, True):
        name = "anch_aware" if aware else "anch_blind"
        cols = anchored_columns(base_specs, daily, var, h, aware, kind)
        Xtr, Xev = train[cols].to_numpy(dtype=float), ev[cols].to_numpy(dtype=float)
        if kind == "yesterday":
            Xtr, Xev = np.column_stack([Xtr, add_anchor_gap(train, var, a_tr)]), np.column_stack([Xev, add_anchor_gap(ev, var, a_ev)])
        per_seed = [a_ev + fit_predict("lightgbm", lgbm_params, s, Xtr, ytr - a_tr, Xev) for s in acfg["seeds"]]
        seed_mae[name] = [float(np.mean(np.abs(p - y))) for p in per_seed]
        out[f"ae_{name}"] = np.mean(np.abs(np.stack(per_seed) - y), axis=0)
        metrics.append({"regime": regime_name, "var": var, "h": h, "model": name, "n_features": Xtr.shape[1],
                        "mae": float(out[f"ae_{name}"].mean()), "seed_mae": seed_mae[name]})
    metrics.append({"regime": regime_name, "var": var, "h": h, "model": "_task", "seconds": round(time.time() - t0, 2),
                    "n_train": int(len(train)), "n_eval": int(len(ev)), "anchor": kind, "fallback_rate_eval": float(fb.mean()),
                    "fallback_rate_train": float(fb_tr.mean())})
    return metrics, out
