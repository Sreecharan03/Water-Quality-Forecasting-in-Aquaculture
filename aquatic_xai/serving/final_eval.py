"""Vectorised evaluation of the SERVING BUNDLE on feature-table rows (Phase 11). Same logic as serving.engine, applied to many origins at once.

Nothing here fits, tunes or selects anything: it only applies the frozen bundle and the frozen baselines.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.models.baselines import seasonal_naive
from aquatic_xai.serving.engine import INPUT_DECIMALS

CELLS = [("DO", 1), ("DO", 4), ("DO", 24), ("pH", 1), ("pH", 4), ("pH", 24), ("Temp", 1), ("Temp", 4), ("Temp", 24)]
ALERT_WINDOWS = [4, 12, 24]


def eval_rows(T: pd.DataFrame, roles: list[str]) -> pd.DataFrame:
    return T[T["role"].isin(roles) & ~T["is_warmup"]]


def y_low_thresholds(T: pd.DataFrame, info: dict) -> dict:
    """10th percentile of each cell's training targets (development ponds, training + validation windows)."""
    base = T["role"].isin(["dev_train", "dev_val"]) & T["pond"].isin(info["dev_ponds"]) & ~T["is_warmup"]
    return {f"{v}_{h}": float(np.quantile(T.loc[base & T[f"y_{v}_h{h}"].notna(), f"y_{v}_h{h}"], 0.10)) for v, h in CELLS}


def chosen_prediction(eng, rows: pd.DataFrame, var: str, h: int) -> np.ndarray:
    c = eng.m["cells"][f"{var}_{h}"]
    cur = rows[f"{var}_cur"].to_numpy(dtype=float)
    yd = rows[f"{var}_yday_tgt_h{h}"].to_numpy(dtype=float)
    if c["method"] == "same_as_now":
        return cur
    if c["method"] == "yesterday":
        return np.where(np.isnan(yd), cur, yd)
    anchor = cur if c["anchor"] == "persistence" else np.where(np.isnan(yd), cur, yd)
    X = rows[c["columns"]].to_numpy(dtype=float)
    if c["anchor"] == "yesterday":
        X = np.column_stack([X, anchor - cur])
    X = np.round(X, INPUT_DECIMALS)
    return anchor + np.mean([b.predict(X) for b in eng._boosters[f"{var}_{h}"]], axis=0)


def forecast_frame(eng, T: pd.DataFrame, rows: pd.DataFrame, var: str, h: int, y_low: float) -> pd.DataFrame:
    ycol, ccol = f"y_{var}_h{h}", f"{var}_cur"
    ev = rows[rows[ycol].notna() & rows[ccol].notna()]
    y = ev[ycol].to_numpy(dtype=float)
    pred = chosen_prediction(eng, ev, var, h)
    r = eng.m["cells"][f"{var}_{h}"]["range"]
    d0, d1 = eng.m["day_hours"]
    hour = pd.to_datetime(ev["ts_ist"]).dt.hour.to_numpy()
    day = (hour >= d0) & (hour < d1)
    q = np.where(day, r["day"], r["night"]) if r["use"] == "daynight" else np.full(len(ev), r["plain"])
    out = ev[["pond", "grid_idx", "block_day", "ts_ist"]].copy()
    out["y"] = y
    out["ae_chosen"] = np.abs(pred - y)
    out["ae_persistence"] = np.abs(ev[ccol].to_numpy(dtype=float) - y)
    out["ae_seasonal_naive"] = np.abs(seasonal_naive(T, ev, var, h, 96) - y)
    out["q"], out["cover"], out["day"], out["low"] = q, (np.abs(pred - y) <= q).astype(float), day, y <= y_low
    return out


def alert_frame(eng, rows: pd.DataFrame, W: int) -> pd.DataFrame:
    a = eng.m["alerts"][str(W)]
    lab = f"lab_W{W}"
    ev = rows[rows[lab].notna() & rows["DO_cur"].notna()]
    X = np.round(ev[a["columns"]].to_numpy(dtype=float), INPUT_DECIMALS)
    p = np.mean([b.predict(X) for b in eng._boosters[f"A_{W}"]], axis=0)
    cur = ev["DO_cur"].to_numpy(dtype=float)
    slope = ev["DO_slope12"].to_numpy(dtype=float)
    yd = ev[f"ydaymin_W{W}"].to_numpy(dtype=float)
    out = ev[["pond", "grid_idx", "block_day", "ts_ist"]].copy()
    out["y"], out["p_model"] = ev[lab].to_numpy(dtype=float), p
    out["p_cal"] = np.interp(p, a["calib"]["x"], a["calib"]["y"])
    out["s_level"] = -cur
    out["s_trend"] = -(cur + np.where(np.isnan(slope), 0.0, slope) * (W * 15 / 60.0))
    out["s_yday"] = -np.where(np.isnan(yd), cur, yd)
    return out
