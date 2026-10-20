"""Deterministic, auditable cleaning. Rows are never silently deleted.

- Raw values are kept in `<var>_raw`; the working column `<var>` is NaN when masked.
- Each cell has a `<var>_status` explaining why it is masked.
- Rows that are collapsed (duplicate timestamps) go to a quarantine table with a reason,
  so n_raw_rows == n_processed_rows + n_quarantined_rows always holds.
- QC flags are parsed into booleans but do NOT mask values: rare low-oxygen events stay.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from aquatic_xai.data.profile import find_columns

CLEAN_VERSION = "clean-v1"
VARS = ("DO", "pH", "Temp")
QC_COLS = ("QC_DT", "QC_DO", "QC_pH")

# flag column -> (source QC column, literal substring)
FLAG_PATTERNS = {
    "flag_gap": ("QC_DT", "time_gap"),
    "flag_flyover": ("QC_DT", "flyover"),
    "flag_do_lt01": ("QC_DO", "DO_<0.1"),
    "flag_do_jump": ("QC_DO", "DO_jump"),
    "flag_do_gt10_am": ("QC_DO", "DO_>10_before_noon"),
    "flag_ph_range": ("QC_pH", "pH_out_of_range"),
    "flag_ph_jump": ("QC_pH", "pH_jump"),
}
# value-quality flags per variable (gap/flyover describe the row, not the value)
VAR_FLAG_COLS = {
    "DO": ["flag_do_lt01", "flag_do_jump", "flag_do_gt10_am"],
    "pH": ["flag_ph_range", "flag_ph_jump"],
    "Temp": [],
}


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    cols = find_columns(list(raw.columns))
    if cols["timestamp"] is None or len(cols["targets"]) < 3:
        raise ValueError(f"cannot detect schema from columns {list(raw.columns)}")
    mapping = {cols["timestamp"]: "ts_ist", cols["targets"]["DO"]: "DO",
               cols["targets"]["pH"]: "pH", cols["targets"]["Temp"]: "Temp"}
    for c in cols["qc"]:
        mapping[c] = "QC_DT" if c.endswith("DateTime") else "QC_DO" if c.endswith("DO") else "QC_pH"
    d = raw.rename(columns=mapping)
    for q in QC_COLS:
        if q not in d:
            d[q] = np.nan
    d["_row"] = np.arange(len(d))
    return d[["_row", "ts_ist", "DO", "pH", "Temp", *QC_COLS]]


def clean_pond(raw: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    c = rules["cleaning"]
    d = standardize(raw)
    d["ts_ist"] = pd.to_datetime(d["ts_ist"], errors="coerce")
    n_raw = len(d)

    bad = d["ts_ist"].isna()
    quarantine = [d[bad].assign(reason="unparsed_timestamp")]
    d = d[~bad].sort_values(["ts_ist", "_row"], kind="stable").reset_index(drop=True)
    for v in VARS:
        d[v] = pd.to_numeric(d[v], errors="coerce")

    grp = d.groupby("ts_ist", sort=False)
    has_dup = bool(d["ts_ist"].duplicated().any())
    conflict = {v: pd.Series(False, index=d.index) for v in VARS}
    merged = {}
    if has_dup:
        for v in VARS:
            conflict[v] = grp[v].transform(lambda s: s.nunique(dropna=False)) > 1
        for q in QC_COLS:
            merged[q] = grp[q].transform(lambda s: ";".join(sorted({str(x) for x in s.dropna()})) or np.nan)

    keep = ~d["ts_ist"].duplicated(keep="first")
    quarantine.append(d[~keep].assign(reason="duplicate_timestamp_row"))
    out = d[keep].copy()
    if has_dup:
        for q in QC_COLS:
            out[q] = merged[q][keep]

    n_conflict_cells = {}
    for v in VARS:
        out[f"{v}_raw"] = out[v]
        vals = out[v]
        st = pd.Series("ok", index=out.index, dtype=object)
        st[vals.isna()] = "null"
        if c["zero_as_missing"]:
            st[vals == 0] = "zero_artifact"
        lo, hi = c["physical_bounds"][v]
        st[(st == "ok") & ((vals < lo) | (vals > hi))] = "out_of_bounds"
        cf = conflict[v][keep]
        st[(st == "ok") & cf] = "dup_conflict"
        n_conflict_cells[v] = int(((st == "dup_conflict")).sum())
        out[f"{v}_status"] = st
        out[v] = vals.where(st == "ok")

    for name, (q, pat) in FLAG_PATTERNS.items():
        out[name] = out[q].fillna("").astype(str).str.contains(pat, regex=False)
    out["ts_utc"] = out["ts_ist"] - pd.Timedelta(minutes=c["timezone"]["utc_offset_minutes"])

    q_df = pd.concat(quarantine, ignore_index=True)
    out = out.drop(columns=["_row"]).reset_index(drop=True)
    q_df = q_df.rename(columns={"_row": "source_row"}).reset_index(drop=True)

    counts = {
        "n_raw_rows": n_raw,
        "n_processed_rows": int(len(out)),
        "n_quarantined_rows": int(len(q_df)),
        "n_unparsed_timestamps": int(bad.sum()),
        "status": {v: {k: int(n) for k, n in out[f"{v}_status"].value_counts().items()} for v in VARS},
    }
    if counts["n_raw_rows"] != counts["n_processed_rows"] + counts["n_quarantined_rows"]:
        raise AssertionError("row accounting broken: rows were lost without a quarantine record")
    return out, q_df, counts


def content_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def dataset_version(raw_commit_sha: str, rules: dict) -> str:
    import json
    payload = json.dumps({"raw": raw_commit_sha, "rules": rules, "code": CLEAN_VERSION}, sort_keys=True)
    return "pp-" + hashlib.sha256(payload.encode()).hexdigest()[:12]
