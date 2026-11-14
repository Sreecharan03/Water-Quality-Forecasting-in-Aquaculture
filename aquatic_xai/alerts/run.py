"""Phase 6 alert task: one (regime, window). LightGBM classifier + three simple baselines' risk scores."""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.experiments.run import find_regime
from aquatic_xai.models.tabular import feature_columns, fit_predict_proba
from aquatic_xai.splits.manifest import regime_masks


def run_alert_task(T: pd.DataFrame, info: dict, cv_folds: int, regime_name: str, W: int, base_specs: list[dict],
                   daily: list[dict], lgbm_params: dict, seeds: list[int], slope_col: str = "DO_slope12", step_min: int = 15) -> pd.DataFrame:
    regime = find_regime(info, cv_folds, regime_name)
    tr_mask, ev_mask = regime_masks(T, info, regime)
    lab = f"lab_W{W}"
    ok = ~T["is_warmup"] & T[lab].notna() & T["DO_cur"].notna()
    train, ev = T[tr_mask & ok], T[ev_mask & ok]
    cols = feature_columns(base_specs, False) + [s["name"] for s in daily] + [f"ydaymin_W{W}"]
    Xtr, Xev = train[cols].to_numpy(dtype=float), ev[cols].to_numpy(dtype=float)
    p = np.mean([fit_predict_proba(lgbm_params, s, Xtr, train[lab].to_numpy(dtype=float), Xev) for s in seeds], axis=0)
    out = ev[["pond", "grid_idx", "block_day", "ts_ist"]].copy()
    cur = ev["DO_cur"].to_numpy(dtype=float)
    slope = ev[slope_col].to_numpy(dtype=float)
    yd = ev[f"ydaymin_W{W}"].to_numpy(dtype=float)
    out["y"], out["p_model"] = ev[lab].to_numpy(dtype=float), p
    out["s_level"] = -cur
    out["s_trend"] = -(cur + np.where(np.isnan(slope), 0.0, slope) * (W * step_min / 60.0))      # slope is per hour; W slots = W*step_min/60 hours
    out["s_yday"] = -np.where(np.isnan(yd), cur, yd)
    return out
