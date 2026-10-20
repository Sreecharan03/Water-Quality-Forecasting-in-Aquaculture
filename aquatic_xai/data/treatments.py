"""Missing-value / quality treatments compared for the Gate 2 decision table.

All treatments are evaluated on the same processed data; nothing here changes it.
Forward fill is causal (uses only past values) and bounded by max_ffill_steps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.data.clean import VAR_FLAG_COLS, VARS
from aquatic_xai.data.profile import usable_origins

TREATMENTS = ["T0_raw_as_is", "T1_zeros_masked", "T2_primary_all_rules", "T3_drop_flagged", "T4_primary_ffill"]


def grid_index(ts: pd.Series, nominal: int, tol: int):
    t0 = ts.iloc[0]
    offs = (ts - t0).dt.total_seconds().to_numpy() / 60.0
    g = np.rint(offs / nominal).astype(int)
    ok = np.abs(offs - g * nominal) <= tol
    return t0, g, ok


def to_grid(row_values: np.ndarray, g: np.ndarray, ok: np.ndarray, n_grid: int):
    arr = np.zeros(n_grid, dtype=bool)
    seen = np.zeros(n_grid, dtype=bool)
    for i in np.where(ok)[0]:
        if seen[g[i]]:
            continue
        seen[g[i]] = True
        arr[g[i]] = row_values[i]
    return arr, seen


def ffill_mask(valid: np.ndarray, k: int) -> np.ndarray:
    """Causal: a missing grid point becomes usable if a real valid point lies within k steps before it."""
    out = valid.copy()
    last = -10**9
    for i, v in enumerate(valid):
        if v:
            last = i
        elif i - last <= k:
            out[i] = True
    return out


def row_valid(p: pd.DataFrame, treatment: str) -> dict:
    out = {}
    for v in VARS:
        raw = p[f"{v}_raw"]
        if treatment == "T0_raw_as_is":
            m = raw.notna()
        elif treatment == "T1_zeros_masked":
            m = raw.notna() & (raw != 0)
        else:
            m = p[f"{v}_status"] == "ok"
        if treatment == "T3_drop_flagged" and VAR_FLAG_COLS[v]:
            m = m & ~p[VAR_FLAG_COLS[v]].any(axis=1)
        out[v] = m.to_numpy()
    return out


def compare_treatments(proc_by_pond: dict, rules: dict) -> list[dict]:
    gcfg, tcfg = rules["grid"], rules["treatments"]
    nominal, tol, k = gcfg["nominal_interval_min"], gcfg["grid_tolerance_min"], tcfg["max_ffill_steps"]
    rows = []
    for tr in TREATMENTS:
        n_valid = {v: 0 for v in VARS}
        do_vals, origins = [], {tuple(s): 0 for s in tcfg["origin_settings"]}
        for p in proc_by_pond.values():
            rv = row_valid(p, "T2_primary_all_rules" if tr == "T4_primary_ffill" else tr)
            for v in VARS:
                n_valid[v] += int(rv[v].sum())
            do_vals.append(p.loc[rv["DO"], "DO_raw"].to_numpy())
            t0, g, ok = grid_index(p["ts_ist"], nominal, tol)
            n_grid = int(g.max()) + 1
            grid = {v: to_grid(rv[v], g, ok, n_grid)[0] for v in VARS}
            look = {v: (ffill_mask(grid[v], k) if tr == "T4_primary_ffill" else grid[v]) for v in VARS}
            look_all = np.logical_and.reduce(list(look.values()))
            for lb, h in origins:
                origins[(lb, h)] += usable_origins(look_all, grid["DO"], lb, h)
        d = np.concatenate(do_vals)
        rows.append({
            "treatment": tr,
            "n_valid_DO": n_valid["DO"], "n_valid_pH": n_valid["pH"], "n_valid_Temp": n_valid["Temp"],
            "DO_median": float(np.median(d)), "DO_p01": float(np.quantile(d, 0.01)), "DO_p99": float(np.quantile(d, 0.99)),
            "n_DO_below_critical": int((d < tcfg["critical_do_mgL"]).sum()),
            "n_DO_below_near_zero": int((d < tcfg["near_zero_do_mgL"]).sum()),
            **{f"origins_L{lb}_h{h}": n for (lb, h), n in origins.items()},
        })
    return rows


def calibration_shift(proc_by_pond: dict, cfg: dict) -> dict:
    pre0, pre1 = (pd.Timestamp(x) for x in cfg["pre_window"])
    post0, post1 = (pd.Timestamp(x) for x in cfg["post_window"])
    wd, sep = pd.Timedelta(days=cfg["window_days"]), pd.Timedelta(days=cfg["separation_days"])
    minp = cfg["min_points"]
    per, summary = [], {v: [] for v in VARS}
    for pond, p in proc_by_pond.items():
        for v in VARS:
            s = p.set_index("ts_ist")[v].dropna()
            idx = s.index
            pre = s[(idx >= pre0) & (idx < pre1)]
            post = s[(idx >= post0) & (idx < post1)]
            if len(pre) < minp or len(post) < minp:
                continue
            delta = float(post.median() - pre.median())
            ref = []
            for st in pd.date_range(idx.min().normalize(), idx.max().normalize(), freq="1D"):
                a = s[(idx >= st) & (idx < st + wd)]
                b = s[(idx >= st + sep) & (idx < st + sep + wd)]
                if len(a) >= minp and len(b) >= minp:
                    ref.append(abs(float(b.median() - a.median())))
            if len(ref) < 5:
                continue
            pct = float((np.array(ref) <= abs(delta)).mean())
            per.append({"pond": pond, "var": v, "delta_median": round(delta, 3), "percentile_vs_typical": round(pct, 3),
                        "n_reference_pairs": len(ref)})
            summary[v].append(pct)
    return {"per_pond": per,
            "summary": {v: {"n_ponds": len(x), "share_ponds_above_90th_pct": round(float(np.mean(np.array(x) >= 0.9)), 3) if x else None,
                            "median_percentile": round(float(np.median(x)), 3) if x else None} for v, x in summary.items()}}


def missingness_profile(proc_by_pond: dict, rules: dict) -> dict:
    nominal, tol = rules["grid"]["nominal_interval_min"], rules["grid"]["grid_tolerance_min"]
    block_missing = np.zeros(6, dtype=np.int64)
    block_total = np.zeros(6, dtype=np.int64)
    cells = {v: {"grid_points_without_row": 0, "zero_artifact": 0, "dup_conflict": 0, "out_of_bounds": 0, "null": 0}
             for v in VARS}
    for p in proc_by_pond.values():
        t0, g, ok = grid_index(p["ts_ist"], nominal, tol)
        n_grid = int(g.max()) + 1
        _, seen = to_grid(np.zeros(len(g), dtype=bool), g, ok, n_grid)
        hours = (t0 + pd.to_timedelta(np.arange(n_grid) * nominal, unit="m")).hour.to_numpy()
        blk = hours // 4
        for b in range(6):
            sel = blk == b
            block_total[b] += int(sel.sum())
            block_missing[b] += int((~seen & sel).sum())
        for v in VARS:
            cells[v]["grid_points_without_row"] += int((~seen).sum())
            for k in ("zero_artifact", "dup_conflict", "out_of_bounds", "null"):
                cells[v][k] += int((p[f"{v}_status"] == k).sum())
    frac = (block_missing / np.maximum(block_total, 1)).round(4).tolist()
    return {"missing_fraction_by_4h_block_IST": dict(zip(["00-04", "04-08", "08-12", "12-16", "16-20", "20-24"], frac)),
            "cells": cells}


def examples_by_category(proc_by_pond: dict, n: int = 2) -> dict:
    cats = {
        "zero_artifact(DO)": lambda p: p["DO_status"] == "zero_artifact",
        "dup_conflict(pH)": lambda p: p["pH_status"] == "dup_conflict",
        "flag DO_<0.1": lambda p: p["flag_do_lt01"],
        "flag DO_jump_>2": lambda p: p["flag_do_jump"],
        "flag pH_out_of_range": lambda p: p["flag_ph_range"],
        "Temp > 33 degC (unflagged, review)": lambda p: p["Temp"] > 33,
    }
    out = {}
    for name, fn in cats.items():
        ex = []
        for pond, p in proc_by_pond.items():
            sel = p[fn(p)]
            for _, r in sel.head(1).iterrows():
                ex.append(f"{pond} {r['ts_ist']} DO_raw={r['DO_raw']} pH_raw={r['pH_raw']} T_raw={r['Temp_raw']}")
            if len(ex) >= n:
                break
        out[name] = ex
    return out
