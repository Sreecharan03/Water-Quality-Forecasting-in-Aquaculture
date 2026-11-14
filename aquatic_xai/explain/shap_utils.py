"""Phase 7/8 helpers: exact TreeSHAP (LightGBM pred_contrib), feature families, stability and deletion-faithfulness tests."""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

FAMILY_ORDER = ["history", "rolling", "daily", "time", "anchor_gap", "quality"]


def family_map(base_specs: list[dict], daily_names: list[str]) -> dict[str, str]:
    m = {s["name"]: s["group"] for s in base_specs}
    for n in daily_names:
        m[n] = "daily"
    return m


def family_of(name: str, fmap: dict[str, str]) -> str:
    if name == "anchor_gap":
        return "anchor_gap"
    if name.startswith("ydaymin_W"):
        return "daily"
    return fmap[name]


def shap_contrib(model, X: np.ndarray) -> np.ndarray:
    """(n_rows, n_features) exact TreeSHAP contributions; the bias column is dropped. Works for LGBMRegressor and LGBMClassifier."""
    return np.asarray(model.booster_.predict(X, pred_contrib=True), dtype=float)[:, :-1]


def mean_abs(contrib: np.ndarray) -> np.ndarray:
    return np.abs(contrib).mean(axis=0)


def safe_spearman(a: np.ndarray, b: np.ndarray) -> float:
    if np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return float("nan")
    return float(spearmanr(a, b).statistic)


def top_k(vec: np.ndarray, k: int) -> list[int]:
    return [int(i) for i in np.argsort(-vec, kind="stable")[:k]]


def family_shares(vec: np.ndarray, names: list[str], fmap: dict[str, str]) -> dict[str, float]:
    tot = float(vec.sum())
    out = {f: 0.0 for f in FAMILY_ORDER}
    for v, n in zip(vec, names):
        out[family_of(n, fmap)] += float(v)
    return {f: (x / tot if tot > 0 else float("nan")) for f, x in out.items() if x > 0 or f in ("history", "rolling", "daily", "time")}


def deletion_losses(predict_loss, X_eval: np.ndarray, medians: np.ndarray, top_idx: list[int], k: int, n_draws: int, seed: int):
    """predict_loss(X) -> per-row loss. Returns (loss_full, loss_top_removed, loss_random_removed_mean_over_draws)."""
    full = predict_loss(X_eval)
    Xt = X_eval.copy()
    Xt[:, top_idx] = medians[top_idx]
    rng = np.random.RandomState(seed)
    acc = np.zeros(len(X_eval))
    for _ in range(n_draws):
        S = rng.choice(X_eval.shape[1], size=k, replace=False)
        Xr = X_eval.copy()
        Xr[:, S] = medians[S]
        acc += predict_loss(Xr)
    return full, predict_loss(Xt), acc / n_draws
