"""Alert evaluation: blocked-bootstrap average precision, and episode-level catch / false-alarm accounting."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def _block_index(d: pd.DataFrame) -> list[np.ndarray]:
    return [np.asarray(ix) for ix in d.groupby(["pond", "block_day"], sort=False).indices.values()]


def ap_ci(d: pd.DataFrame, y: str, scores: list[str], B: int, seed: int, level: float) -> dict:
    """Point average precision per score, and paired bootstrap intervals for (first score minus each other score)."""
    d = d.reset_index(drop=True)
    yv, blocks = d[y].to_numpy(dtype=int), _block_index(d)
    S = {s: d[s].to_numpy(dtype=float) for s in scores}
    pt = {s: float(average_precision_score(yv, S[s])) for s in scores}
    rng = np.random.RandomState(seed)
    diffs = {s: [] for s in scores[1:]}
    base = {s: [] for s in scores}
    for _ in range(B):
        idx = np.concatenate([blocks[i] for i in rng.randint(0, len(blocks), len(blocks))])
        if yv[idx].sum() == 0:
            continue
        ap = {s: average_precision_score(yv[idx], S[s][idx]) for s in scores}
        for s in scores:
            base[s].append(ap[s])
        for s in scores[1:]:
            diffs[s].append(ap[scores[0]] - ap[s])
    lo, hi = (100 - level) / 2, 100 - (100 - level) / 2
    return {"ap": pt, "ap_ci": {s: (float(np.percentile(v, lo)), float(np.percentile(v, hi))) for s, v in base.items()},
            "diff": {s: (pt[scores[0]] - pt[s], float(np.percentile(v, lo)), float(np.percentile(v, hi))) for s, v in diffs.items()}}


def episode_stats(rows: pd.DataFrame, onsets: dict, score: str, thresh: float, lead_min: int, lead_max: int) -> dict:
    """rows: evaluation rows (pond, grid_idx, block_day, y, score). onsets: pond -> onset grid indices.
    Caught = some origin lead_min..lead_max slots before the onset has score >= thresh."""
    n_ep = caught = excluded = 0
    leads = []
    for pond, g in rows.groupby("pond", sort=False):
        gi, sc = g["grid_idx"].to_numpy(), g[score].to_numpy()
        for on in onsets.get(pond, []):
            cand = (gi >= on - lead_max) & (gi <= on - lead_min)
            if not cand.any():
                excluded += 1
                continue
            n_ep += 1
            fired = cand & (sc >= thresh)
            if fired.any():
                caught += 1
                leads.append((on - gi[fired].min()) / 4.0)
    fa = rows[(rows["y"] == 0) & (rows[score] >= thresh)]
    days = rows.groupby(["pond", "block_day"]).ngroups
    nfa = fa.groupby(["pond", "block_day"]).ngroups
    return {"episodes": n_ep, "caught": caught, "excluded_no_origins": excluded, "recall": caught / n_ep if n_ep else float("nan"),
            "median_lead_h": float(np.median(leads)) if leads else float("nan"),
            "false_alarm_pond_days": nfa, "pond_days": days, "false_alarm_day_share": nfa / days if days else float("nan")}


def match_recall_threshold(rows: pd.DataFrame, onsets: dict, score: str, target_recall: float, lead_min: int, lead_max: int):
    """Strictest threshold (fewest alerts) whose episode recall is >= target; if impossible, the loosest one."""
    qs = np.unique(np.quantile(rows[score].to_numpy(dtype=float), np.linspace(0, 1, 201)))
    best = None
    for t in qs[::-1]:
        st = episode_stats(rows, onsets, score, t, lead_min, lead_max)
        best = (float(t), st)
        if st["recall"] >= target_recall:
            break
    return best
