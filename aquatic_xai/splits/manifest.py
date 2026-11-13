"""Row-level split assignments, evaluation regimes, independence checks and the frozen manifest."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from aquatic_xai.splits.grouped import assign_folds, pick_sealed
from aquatic_xai.splits.temporal import choose_cutoffs, window_labels

SPLIT_CODE_VERSION = "split-v1"
META_COLS = ["pond", "grid_idx", "ts_ist", "is_warmup", "ts_target_h24"]


def split_version(feature_version: str, cfg: dict) -> str:
    payload = json.dumps({"features": feature_version, "cfg": cfg, "code": SPLIT_CODE_VERSION}, sort_keys=True)
    return "sp-" + hashlib.sha256(payload.encode()).hexdigest()[:12]


def build_assignments(table: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """`table` needs META_COLS plus the columns named in cfg['usable_requires']."""
    emb = pd.Timedelta(minutes=cfg["embargo_steps"] * cfg["nominal_interval_min"])
    if cfg["embargo_steps"] < cfg["max_lookback_steps"] + cfg["max_horizon_steps"]:
        raise ValueError("embargo shorter than max lookback + max horizon")
    a = table[META_COLS].copy()
    a["usable"] = (~table["is_warmup"]) & table[cfg["usable_requires"]].notna().all(axis=1)
    t1, t2 = choose_cutoffs(a.loc[~a["is_warmup"], "ts_ist"], cfg["fractions"])
    a["window"] = window_labels(a["ts_ist"], t1, t2, emb)

    test_counts = a[(a["window"] == "test") & a["usable"]].groupby("pond").size().to_dict()
    ponds = sorted(a["pond"].unique())
    eligible = [p for p in ponds if test_counts.get(p, 0) >= cfg["min_test_origins"]]
    sealed = pick_sealed(eligible, cfg["n_sealed_ponds"], cfg["seed"])
    dev = [p for p in ponds if p not in sealed]
    val_counts = a[(a["window"] == "val") & a["usable"] & a["pond"].isin(dev)].groupby("pond").size().to_dict()
    folds = assign_folds({p: val_counts.get(p, 0) for p in dev}, cfg["cv_folds"], cfg["min_val_origins"])

    is_sealed = a["pond"].isin(sealed)
    role = np.where(a["is_warmup"], "warmup_excluded", "")
    role = np.where((role == "") & a["window"].str.startswith("embargo"), "embargo", role)
    role = np.where((role == "") & is_sealed & (a["window"] == "test"), "unseen_pond_test", role)
    role = np.where((role == "") & is_sealed, "sealed_pond_unused", role)
    role = np.where((role == "") & (a["window"] == "train"), "dev_train", role)
    role = np.where((role == "") & (a["window"] == "val"), "dev_val", role)
    role = np.where((role == "") & (a["window"] == "test"), "seen_pond_test", role)
    a["role"] = role
    a["fold"] = a["pond"].map(lambda p: -2 if p in sealed else folds[p])
    a["block_day"] = a["ts_ist"].dt.strftime("%Y-%m-%d")      # unit for blocked bootstrap (pond x calendar day)

    info = {"cutoff_train_end": str(t1), "cutoff_val_end": str(t2), "embargo_hours": emb.total_seconds() / 3600,
            "sealed_ponds": sealed, "dev_ponds": dev, "folds": {p: int(f) for p, f in folds.items()},
            "eligible_sealed_ponds": eligible, "seed": cfg["seed"]}
    return a, info


def regimes(info: dict, k: int) -> list[dict]:
    """Declarative evaluation regimes. Training pools never contain sealed ponds or any test-window rows,
    except the two final regimes, which are evaluated exactly once."""
    R = [{"name": "dev_future_seen_ponds", "kind": "future_seen",
          "train": {"roles": ["dev_train"], "ponds": "dev"}, "eval": {"roles": ["dev_val"], "ponds": "dev"}}]
    for f in range(k):
        held = sorted(p for p, v in info["folds"].items() if v == f)
        rest = sorted(p for p in info["dev_ponds"] if p not in held)
        R.append({"name": f"dev_future_unseen_fold{f}", "kind": "future_unseen",
                  "train": {"roles": ["dev_train"], "ponds": rest}, "eval": {"roles": ["dev_val"], "ponds": held}})
        R.append({"name": f"diagnostic_unseen_sametime_fold{f}", "kind": "diagnostic_optimistic",
                  "train": {"roles": ["dev_train"], "ponds": rest}, "eval": {"roles": ["dev_train"], "ponds": held}})
    R.append({"name": "FINAL_seen_ponds_future", "kind": "final",
              "train": {"roles": ["dev_train", "dev_val"], "ponds": "dev"}, "eval": {"roles": ["seen_pond_test"], "ponds": "dev"}})
    R.append({"name": "FINAL_unseen_ponds_future", "kind": "final",
              "train": {"roles": ["dev_train", "dev_val"], "ponds": "dev"}, "eval": {"roles": ["unseen_pond_test"], "ponds": info["sealed_ponds"]}})
    return R


def regime_masks(a: pd.DataFrame, info: dict, r: dict) -> tuple[pd.Series, pd.Series]:
    def sel(side: dict) -> pd.Series:
        ponds = info["dev_ponds"] if side["ponds"] == "dev" else side["ponds"]
        return a["role"].isin(side["roles"]) & a["pond"].isin(ponds)
    return sel(r["train"]), sel(r["eval"])


def check_assignments(a: pd.DataFrame, info: dict, cfg: dict) -> dict:
    out: dict = {}
    out["unique_rows"] = bool(not a.duplicated(["pond", "grid_idx"]).any())
    out["row_accounting"] = int(len(a))
    horizon = pd.Timedelta(minutes=cfg["max_horizon_steps"] * cfg["nominal_interval_min"])
    lookback = pd.Timedelta(minutes=cfg["max_lookback_steps"] * cfg["nominal_interval_min"])
    w = a[~a["is_warmup"]]

    def gap(early: str, late: str) -> float:
        e, l = w[w["window"] == early], w[w["window"] == late]
        return float(((l["ts_ist"].min() - lookback) - e["ts_target_h24"].max()).total_seconds() / 3600)

    out["gap_hours_train_to_val"] = gap("train", "val")
    out["gap_hours_val_to_test"] = gap("val", "test")
    out["gap_hours_train_to_test"] = gap("train", "test")
    out["embargo_ok"] = bool(min(out["gap_hours_train_to_val"], out["gap_hours_val_to_test"], out["gap_hours_train_to_test"]) >= 0)

    sealed = a[a["pond"].isin(info["sealed_ponds"])]
    out["sealed_rows_in_dev_roles"] = int(sealed["role"].isin(["dev_train", "dev_val", "seen_pond_test"]).sum())
    out["sealed_ponds_disjoint_from_dev"] = bool(not set(info["sealed_ponds"]) & set(info["dev_ponds"]))

    results = []
    for r in regimes(info, cfg["cv_folds"]):
        tr, ev = regime_masks(a, info, r)
        row_overlap = int((tr & ev).sum())
        pond_overlap = sorted(set(a.loc[tr, "pond"]) & set(a.loc[ev, "pond"]))
        future = r["kind"] in ("future_seen", "future_unseen", "final")
        gap_h = None
        if future:
            gap_h = float(((a.loc[ev & ~a["is_warmup"], "ts_ist"].min() - lookback) - a.loc[tr & ~a["is_warmup"], "ts_target_h24"].max()).total_seconds() / 3600)
        unseen = r["kind"] in ("future_unseen", "diagnostic_optimistic") or r["name"] == "FINAL_unseen_ponds_future"
        ok = row_overlap == 0 and (not unseen or not pond_overlap) and (gap_h is None or gap_h >= 0)
        ok = ok and not (set(info["sealed_ponds"]) & set(a.loc[tr, "pond"]))
        results.append({"regime": r["name"], "kind": r["kind"], "train_rows": int(tr.sum()), "eval_rows": int(ev.sum()),
                        "eval_ponds": int(a.loc[ev, "pond"].nunique()), "row_overlap": row_overlap,
                        "pond_overlap": pond_overlap, "gap_hours": gap_h, "pass": bool(ok)})
    out["regimes"] = results
    out["all_regimes_pass"] = bool(all(x["pass"] for x in results))
    out["all_pass"] = bool(out["unique_rows"] and out["embargo_ok"] and out["sealed_rows_in_dev_roles"] == 0
                           and out["sealed_ponds_disjoint_from_dev"] and out["all_regimes_pass"])
    return out


def content_hash(a: pd.DataFrame) -> str:
    cols = ["pond", "grid_idx", "window", "role", "fold", "block_day"]
    return hashlib.sha256(a[cols].to_csv(index=False).encode()).hexdigest()


def role_counts(a: pd.DataFrame, table: pd.DataFrame, horizons=(1, 4, 24), variables=("DO", "pH", "Temp")) -> pd.DataFrame:
    rows = []
    for role, g in a.groupby("role"):
        t = table.loc[g.index]
        r = {"role": role, "origins": len(g), "ponds": g["pond"].nunique()}
        for v in variables:
            for h in horizons:
                r[f"{v}_h{h}_valid_target"] = int(t[f"y_{v}_h{h}"].notna().sum())
        rows.append(r)
    return pd.DataFrame(rows).set_index("role")


def gantt_text(a: pd.DataFrame, info: dict) -> str:
    """One character per calendar day per pond: T train, V val, X seen-pond test, S unseen-pond test (sealed),
    o sealed pond (unused), . no data. A day takes the role of most of its rows."""
    d = a[~a["is_warmup"] & (a["role"] != "embargo")].copy()
    d["day"] = d["ts_ist"].dt.normalize()
    days = pd.date_range(d["day"].min(), d["day"].max(), freq="D")
    sym = {"dev_train": "T", "dev_val": "V", "seen_pond_test": "X", "unseen_pond_test": "S", "sealed_pond_unused": "o"}
    t1, t2 = pd.Timestamp(info["cutoff_train_end"]), pd.Timestamp(info["cutoff_val_end"])
    head = "".join("|" if (x == t1 or x == t2) else " " for x in days)
    lines = [f"{'':14s} {head}   (| = cutoffs {t1.date()} and {t2.date()}; first day {days[0].date()}, last {days[-1].date()})"]
    for p in sorted(a["pond"].unique()):
        g = d[d["pond"] == p]
        mode = g.groupby("day")["role"].agg(lambda s: s.value_counts().index[0])
        row = "".join(sym.get(mode.get(x), ".") if x in mode.index else "." for x in days)
        tag = "SEALED" if p in info["sealed_ponds"] else f"fold {info['folds'].get(p, -1)}"
        lines.append(f"{p:14s} {row}   {tag}")
    return "\n".join(lines)
