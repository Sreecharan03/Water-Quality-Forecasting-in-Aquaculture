"""Per-pond data inventory. Pure pandas/numpy so it is unit-testable; executed on Modal.

Nothing here cleans, drops or imputes. Zeros and flagged rows are counted, not removed.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

TARGET_PATTERNS = {"DO": r"^DO\b", "pH": r"^pH\b", "Temp": r"^temp"}


def find_columns(columns: list[str]) -> dict:
    found: dict = {"timestamp": None, "targets": {}, "qc": []}
    for c in columns:
        if found["timestamp"] is None and re.search(r"time", c, re.I) and not c.startswith("QC_"):
            found["timestamp"] = c
        for key, pat in TARGET_PATTERNS.items():
            if key not in found["targets"] and re.search(pat, c, re.I):
                found["targets"][key] = c
        if c.startswith("QC_Flag"):
            found["qc"].append(c)
    return found


def usable_origins(valid_all: np.ndarray, valid_target: np.ndarray, lookback: int, horizon: int) -> int:
    """Count grid origins g where the last `lookback` grid points (incl. g) are all valid
    and the target at g+horizon is a valid observation. Missing grid points count as invalid."""
    n = len(valid_all)
    if n <= horizon + lookback:
        return 0
    cs = np.concatenate([[0], np.cumsum(valid_all.astype(np.int64))])
    count = 0
    for g in range(lookback - 1, n - horizon):
        if cs[g + 1] - cs[g + 1 - lookback] == lookback and valid_target[g + horizon]:
            count += 1
    return count


def profile_pond(df: pd.DataFrame, cfg: dict) -> dict:
    nominal = cfg["nominal_interval_min"]
    gap_thr = cfg["gap_threshold_min"]
    tol = cfg["grid_tolerance_min"]
    cols = find_columns(list(df.columns))
    out: dict = {"n_rows": int(len(df)), "columns": list(df.columns), "detected": cols}
    if cols["timestamp"] is None or len(cols["targets"]) < 3:
        out["error"] = "could not detect timestamp and DO/pH/Temp columns"
        return out

    raw_ts = df[cols["timestamp"]].astype(str)
    ts = pd.to_datetime(raw_ts, errors="coerce")
    out["timestamp_sample"] = raw_ts.iloc[:2].tolist()
    out["timestamp_has_tz_marker"] = bool(raw_ts.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).any())
    out["n_unparsed_timestamps"] = int(ts.isna().sum())

    out["n_exact_duplicate_rows"] = int(df.duplicated().sum())
    out["n_duplicate_timestamps"] = int(ts.duplicated().sum())
    out["n_out_of_order"] = int((ts.diff().dt.total_seconds() < 0).sum())

    order = ts.argsort(kind="stable")
    df_s = df.iloc[order].reset_index(drop=True)
    ts_s = ts.iloc[order].reset_index(drop=True)
    keep = ts_s.notna() & ~ts_s.duplicated(keep="first")
    df_s, ts_s = df_s[keep].reset_index(drop=True), ts_s[keep].reset_index(drop=True)
    out["first_timestamp"] = str(ts_s.iloc[0]) if len(ts_s) else None
    out["last_timestamp"] = str(ts_s.iloc[-1]) if len(ts_s) else None
    out["span_days"] = round((ts_s.iloc[-1] - ts_s.iloc[0]).total_seconds() / 86400, 2) if len(ts_s) > 1 else 0

    dmin = ts_s.diff().dt.total_seconds().dropna() / 60.0
    out["interval_min"] = {
        "median": float(dmin.median()) if len(dmin) else None,
        "pct_within_1min_of_nominal": round(float(((dmin - nominal).abs() <= 1).mean() * 100), 2) if len(dmin) else None,
        "top_values": {str(k): int(v) for k, v in dmin.round(0).value_counts().head(6).items()},
    }
    gaps = dmin[dmin > gap_thr]
    out["gaps"] = {
        "n_gaps_over_threshold": int(len(gaps)),
        "max_gap_hours": round(float(gaps.max() / 60), 2) if len(gaps) else 0,
        "n_gaps_over_1h": int((gaps > 60).sum()),
        "n_gaps_over_6h": int((gaps > 360).sum()),
        "total_missing_minutes_in_gaps": round(float((gaps - nominal).sum()), 1),
    }

    targets = {}
    valid_by = {}
    for key, c in cols["targets"].items():
        s = pd.to_numeric(df_s[c], errors="coerce")
        nonnum = int(df_s[c].notna().sum() - s.notna().sum())
        nz = s[(s.notna()) & (s != 0)]
        targets[key] = {
            "column": c,
            "n_null": int(s.isna().sum()),
            "n_non_numeric": nonnum,
            "n_zero": int((s == 0).sum()),
            "min_nonzero": float(nz.min()) if len(nz) else None,
            "p01": float(nz.quantile(0.01)) if len(nz) else None,
            "median": float(nz.median()) if len(nz) else None,
            "p99": float(nz.quantile(0.99)) if len(nz) else None,
            "max": float(nz.max()) if len(nz) else None,
        }
        valid_by[key] = (s.notna() & (s != 0)).to_numpy()
    out["targets"] = targets
    valid_all_rows = np.logical_and.reduce(list(valid_by.values()))
    out["n_rows_all_three_valid"] = int(valid_all_rows.sum())

    out["qc_flags"] = {c: {str(k): int(v) for k, v in df_s[c].dropna().astype(str).value_counts().head(10).items()}
                       for c in cols["qc"]}

    # Snap to the nominal grid (tolerance-checked), never inventing observations.
    t0 = ts_s.iloc[0]
    offs = (ts_s - t0).dt.total_seconds().to_numpy() / 60.0
    g = np.rint(offs / nominal).astype(int)
    resid = np.abs(offs - g * nominal)
    ok = resid <= tol
    out["grid"] = {"n_off_grid_rows": int((~ok).sum()), "n_grid_points": int(g.max() + 1)}
    n_grid = int(g.max() + 1)
    grid_valid_all = np.zeros(n_grid, dtype=bool)
    grid_valid_t = {k: np.zeros(n_grid, dtype=bool) for k in valid_by}
    seen = np.zeros(n_grid, dtype=bool)
    collisions = 0
    for i in np.where(ok)[0]:
        gi = g[i]
        if seen[gi]:
            collisions += 1
            continue
        seen[gi] = True
        grid_valid_all[gi] = valid_all_rows[i]
        for k in valid_by:
            grid_valid_t[k][gi] = valid_by[k][i]
    out["grid"]["n_collisions"] = collisions

    # Longest contiguous valid run (all three variables valid, consecutive grid points).
    best = cur = runs = 0
    for v in grid_valid_all:
        if v:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    runs = int(((grid_valid_all[1:] & ~grid_valid_all[:-1]).sum()) + (1 if grid_valid_all[:1].any() else 0))
    out["longest_valid_run_steps"] = int(best)
    out["n_valid_runs"] = runs

    out["usable_origins"] = {
        f"L{lb}_h{h}_{k}": usable_origins(grid_valid_all, grid_valid_t[k], lb, h)
        for lb in cfg["lookback_steps"] for h in cfg["horizons_steps"] for k in valid_by
    }
    return out


def to_markdown(source_manifest: dict, per_pond: dict, cfg: dict) -> str:
    L = [f"# Phase 1 data inventory (source commit `{source_manifest['commit_sha'][:12]}`)", "",
         f"- Source: {source_manifest['repo']} | retrieved {source_manifest['retrieved_utc']}",
         f"- Files: {source_manifest['n_files']} | bytes: {source_manifest['total_bytes']}",
         f"- Licence state: {source_manifest['licence_state']}", "",
         "## Per-pond overview", "",
         "| pond | rows | first | last | days | %15min | gaps>20m | max gap h | dupTS | ooo | zeros DO/pH/T | nullDO/pH/T | valid rows | longest run |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for pond, p in per_pond.items():
        if "error" in p:
            L.append(f"| {pond} | {p['n_rows']} | ERROR: {p['error']} |")
            continue
        t = p["targets"]
        L.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {}/{}/{} | {}/{}/{} | {} | {} |".format(
            pond, p["n_rows"], (p["first_timestamp"] or "")[:16], (p["last_timestamp"] or "")[:16], p["span_days"],
            p["interval_min"]["pct_within_1min_of_nominal"], p["gaps"]["n_gaps_over_threshold"],
            p["gaps"]["max_gap_hours"], p["n_duplicate_timestamps"], p["n_out_of_order"],
            t["DO"]["n_zero"], t["pH"]["n_zero"], t["Temp"]["n_zero"],
            t["DO"]["n_null"], t["pH"]["n_null"], t["Temp"]["n_null"],
            p["n_rows_all_three_valid"], p["longest_valid_run_steps"]))
    L += ["", "## Usable forecast origins (all 3 variables valid over lookback; target valid at t+h)", "",
          "Counts are for the DO target; see JSON for pH and Temp.", "",
          "| pond | " + " | ".join(f"L{lb}/h{h}" for lb in cfg["lookback_steps"] for h in cfg["horizons_steps"]) + " |",
          "|---|" + "---|" * (len(cfg["lookback_steps"]) * len(cfg["horizons_steps"]))]
    for pond, p in per_pond.items():
        if "usable_origins" in p:
            L.append(f"| {pond} | " + " | ".join(str(p["usable_origins"][f"L{lb}_h{h}_DO"])
                                                   for lb in cfg["lookback_steps"] for h in cfg["horizons_steps"]) + " |")
    L += ["", "## Value ranges (non-zero, non-null), DO / pH / Temp", "",
          "| pond | DO min/med/max | pH min/med/max | Temp min/med/max |", "|---|---|---|---|"]
    for pond, p in per_pond.items():
        if "targets" in p:
            f = lambda k: "{:.2f}/{:.2f}/{:.2f}".format(*(p["targets"][k][x] or float("nan") for x in ("min_nonzero", "median", "max")))
            L.append(f"| {pond} | {f('DO')} | {f('pH')} | {f('Temp')} |")
    first = next(iter(per_pond.values()))
    L += ["", "## Detected schema (first pond)", "", f"- columns: {first.get('columns')}",
          f"- detected: {first.get('detected')}",
          f"- timestamp sample: {first.get('timestamp_sample')}; tz marker present: {first.get('timestamp_has_tz_marker')}"]
    flags: dict = {}
    for p in per_pond.values():
        for c, d in p.get("qc_flags", {}).items():
            for k, v in d.items():
                flags.setdefault(c, {}).setdefault(k, 0)
                flags[c][k] += v
    L += ["", "## QC flag counts (all ponds, top values per column)", ""]
    for c, d in flags.items():
        L.append(f"- **{c}**: " + ", ".join(f"{k}={v}" for k, v in sorted(d.items(), key=lambda x: -x[1])[:10]))
    return "\n".join(L)
