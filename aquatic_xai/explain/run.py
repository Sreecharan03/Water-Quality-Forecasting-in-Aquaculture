"""Phase 7/8 tasks: fit the evaluated model, compute SHAP on validation-window rows, stability inputs and the deletion test."""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.experiments.run import find_regime
from aquatic_xai.explain.shap_utils import deletion_losses, mean_abs, shap_contrib, top_k
from aquatic_xai.models.anchored import add_anchor_gap, anchor_for, anchored_columns
from aquatic_xai.models.tabular import feature_columns, make_model
from aquatic_xai.splits.manifest import regime_masks

K_TOP, N_DRAWS, DEL_SEED, SUBSAMPLE = 5, 50, 20261113, 5000


def _fit_cls(params: dict, seed: int, X: np.ndarray, y: np.ndarray):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(**params, random_state=seed, n_jobs=2, verbose=-1)
    return m.fit(X, y.astype(int))


def _prepare(train_X, medians_source=None):
    med = np.nanmedian(train_X, axis=0)
    return np.where(np.isnan(med), 0.0, med)


def _common(model_fn, shap_model_seed0, Xtr, Xev, loss_fn, seeds_models, names):
    """Shared: per-seed mean |SHAP| on eval rows, halves (seed 0), top-5 by training subsample, deletion losses (seed 0)."""
    out = {"names": names, "mean_abs": {}}
    contribs = {}
    for s, m in seeds_models.items():
        c = shap_contrib(m, Xev)
        contribs[s] = c
        out["mean_abs"][str(s)] = mean_abs(c).tolist()
    return out, contribs


def explain_forecast_task(T, info, cv_folds, regime_name, var, h, base_specs, daily, lgbm_params, anchors, seeds):
    regime = find_regime(info, cv_folds, regime_name)
    tr_mask, ev_mask = regime_masks(T, info, regime)
    ycol, ccol = f"y_{var}_h{h}", f"{var}_cur"
    kind = anchors[h]
    ok = ~T["is_warmup"] & T[ycol].notna() & T[ccol].notna()
    train, ev = T[tr_mask & ok], T[ev_mask & ok]
    y, ytr = ev[ycol].to_numpy(dtype=float), train[ycol].to_numpy(dtype=float)
    a_tr, _ = anchor_for(train, var, h, kind)
    a_ev, _ = anchor_for(ev, var, h, kind)
    cols = anchored_columns(base_specs, daily, var, h, False, kind)
    Xtr, Xev = train[cols].to_numpy(dtype=float), ev[cols].to_numpy(dtype=float)
    names = list(cols)
    if kind == "yesterday":
        Xtr, Xev = np.column_stack([Xtr, add_anchor_gap(train, var, a_tr)]), np.column_stack([Xev, add_anchor_gap(ev, var, a_ev)])
        names.append("anchor_gap")
    models = {s: make_model("lightgbm", lgbm_params, s).fit(Xtr, ytr - a_tr) for s in seeds}
    res, contribs = _common(None, None, Xtr, Xev, None, models, names)
    # time halves (seed 0)
    ts = pd.to_datetime(ev["ts_ist"]).to_numpy()
    first = ts <= np.median(ts.astype("int64")).astype("datetime64[ns]")
    res["half_first"], res["half_second"] = mean_abs(contribs[seeds[0]][first]).tolist(), mean_abs(contribs[seeds[0]][~first]).tolist()
    # top-5 from a training subsample (non-circular), then deletion test with seed-0 model
    m0 = models[seeds[0]]
    rng = np.random.RandomState(DEL_SEED)
    sub = rng.choice(len(Xtr), size=min(SUBSAMPLE, len(Xtr)), replace=False)
    top = top_k(mean_abs(shap_contrib(m0, Xtr[sub])), K_TOP)
    med = _prepare(Xtr)
    loss = lambda X: np.abs(a_ev + m0.predict(X) - y)
    lf, lt, lr = deletion_losses(loss, Xev, med, top, K_TOP, N_DRAWS, DEL_SEED)
    res.update({"top5_train_subsample": [names[i] for i in top], "n_train": int(len(train)), "n_eval": int(len(ev)), "anchor": kind,
                "mae_full": float(lf.mean()), "mae_top5_removed": float(lt.mean()), "mae_random5_removed": float(lr.mean())})
    frame = ev[["pond", "block_day"]].copy()
    frame["loss_full"], frame["loss_top"], frame["loss_rand"] = lf, lt, lr
    # two example rows (seeded), signed contributions
    ex = []
    for i in np.random.RandomState(DEL_SEED + 1).choice(len(Xev), size=min(2, len(Xev)), replace=False):
        c = contribs[seeds[0]][i]
        j = top_k(np.abs(c), 5)
        ex.append({"hour_sin": float(ev["hour_sin"].iloc[i]), "anchor": float(a_ev[i]), "pred_correction": float(c.sum()),
                   "top": [{"feature": names[k], "value": None if np.isnan(Xev[i, k]) else float(Xev[i, k]), "shap": float(c[k])} for k in j]})
    res["examples"] = ex
    return res, frame


def explain_alert_task(T, info, cv_folds, regime_name, W, base_specs, daily, lgbm_params, seeds):
    regime = find_regime(info, cv_folds, regime_name)
    tr_mask, ev_mask = regime_masks(T, info, regime)
    lab = f"lab_W{W}"
    ok = ~T["is_warmup"] & T[lab].notna() & T["DO_cur"].notna()
    train, ev = T[tr_mask & ok], T[ev_mask & ok]
    cols = feature_columns(base_specs, False) + [s["name"] for s in daily] + [f"ydaymin_W{W}"]
    Xtr, Xev = train[cols].to_numpy(dtype=float), ev[cols].to_numpy(dtype=float)
    ytr, y = train[lab].to_numpy(dtype=float), ev[lab].to_numpy(dtype=float)
    names = list(cols)
    models = {s: _fit_cls(lgbm_params, s, Xtr, ytr) for s in seeds}
    res, contribs = _common(None, None, Xtr, Xev, None, models, names)
    ts = pd.to_datetime(ev["ts_ist"]).to_numpy()
    first = ts <= np.median(ts.astype("int64")).astype("datetime64[ns]")
    res["half_first"], res["half_second"] = mean_abs(contribs[seeds[0]][first]).tolist(), mean_abs(contribs[seeds[0]][~first]).tolist()
    m0 = models[seeds[0]]
    rng = np.random.RandomState(DEL_SEED)
    sub = rng.choice(len(Xtr), size=min(SUBSAMPLE, len(Xtr)), replace=False)
    top = top_k(mean_abs(shap_contrib(m0, Xtr[sub])), K_TOP)
    med = _prepare(Xtr)

    def loss(X):
        p = np.clip(m0.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))

    lf, lt, lr = deletion_losses(loss, Xev, med, top, K_TOP, N_DRAWS, DEL_SEED)
    res.update({"top5_train_subsample": [names[i] for i in top], "n_train": int(len(train)), "n_eval": int(len(ev)),
                "logloss_full": float(lf.mean()), "logloss_top5_removed": float(lt.mean()), "logloss_random5_removed": float(lr.mean()),
                "event_rate": float(y.mean())})
    frame = ev[["pond", "block_day"]].copy()
    frame["loss_full"], frame["loss_top"], frame["loss_rand"] = lf, lt, lr
    p_full = m0.predict_proba(Xev)[:, 1]
    cand = np.where((y == 1) & (p_full > 0.8))[0]
    ex = []
    if len(cand):
        for i in np.random.RandomState(DEL_SEED + 2).choice(cand, size=min(3, len(cand)), replace=False):
            c = contribs[seeds[0]][i]
            j = top_k(np.abs(c), 5)
            ex.append({"p_event": float(p_full[i]), "top": [{"feature": names[k], "value": None if np.isnan(Xev[i, k]) else float(Xev[i, k]), "shap_log_odds": float(c[k])} for k in j]})
    res["examples"] = ex
    return res, frame
