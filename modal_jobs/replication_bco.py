"""Phase 1b-R: replicate the frozen method on BCO-DMO 988873 (salt-marsh ponds). Contract: configs/replication_bco.yaml.

    modal run -m modal_jobs.replication_bco::stage1 --git-sha <sha>     # data, features, split, integrity checks (no models)
    modal run -m modal_jobs.replication_bco::stage2 --git-sha <sha>     # models, ranges, alert, report (only after stage 1 passes)
"""
from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image

EXT = "external/bco-988873"
_CACHE: dict = {}


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _cfg() -> dict:
    return _yaml("replication_bco.yaml")


def _fcfg(c: dict) -> dict:
    return {"variables": ["DO", "pH", "Temp"], **c["grid"]["features"], "horizons": c["grid"]["horizons_steps"]}


def _scfg(c: dict) -> dict:
    s, g = c["split"], c["grid"]
    h = max(g["horizons_steps"])
    return {"nominal_interval_min": g["nominal_interval_min"], "embargo_steps": s["embargo_steps"], "max_lookback_steps": max(g["features"]["lags"]),
            "max_horizon_steps": h, "long_horizon_steps": h, "fractions": s["fractions"], "n_sealed_ponds": s["n_sealed_ponds"], "seed": s["seed"],
            "cv_folds": s["cv_folds"], "min_val_origins": s["min_val_origins"], "min_test_origins": s["min_test_origins"],
            "usable_requires": [f"y_{v}_h{h}" for v in ("DO", "pH", "Temp")]}


def _raw_frame(c: dict):
    import pandas as pd
    from aquatic_xai.data.external import do_mg_per_l
    p = Path(DATA_MOUNT, EXT, "raw", "988873_v1_salt_pond_monitoring.csv")
    df = pd.read_csv(p, na_values=["", "nd", "NaN"])
    df["DO_mgL"] = do_mg_per_l(df["DOconc"], df["salinity"])
    return df


def _version(c: dict, extra: str) -> str:
    payload = json.dumps({"md5": c["dataset"]["md5"], "grid": c["grid"], "do": c["dataset"]["do_conversion"], "code": extra}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def build_data(git_sha: str) -> dict:
    """Download (once), verify md5, build 30-minute grids, causal features and targets per pond. Write-once."""
    import numpy as np
    import pandas as pd
    from aquatic_xai.data.clean import content_hash
    from aquatic_xai.data.external import prepare_pond, to_grid
    from aquatic_xai.features.build import FEATURE_CODE_VERSION, compute_features, make_targets
    c = _cfg()
    data_vol.reload()
    raw_path = Path(DATA_MOUNT, EXT, "raw", "988873_v1_salt_pond_monitoring.csv")
    if not raw_path.exists():
        url = "https://datadocs.bco-dmo.org/dataset/988873/file/7D5YK41uEZBrB6/988873_v1_salt_pond_monitoring.csv"
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-data-check"}), timeout=300).read()
        assert hashlib.md5(raw).hexdigest() == c["dataset"]["md5"], "md5 mismatch"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
    assert hashlib.md5(raw_path.read_bytes()).hexdigest() == c["dataset"]["md5"]
    df = _raw_frame(c)
    fcfg, nominal = _fcfg(c), c["grid"]["nominal_interval_min"]
    ver = "bco-" + _version(c, "bco-feat-v1+" + FEATURE_CODE_VERSION)
    out_dir = Path(DATA_MOUNT, EXT, "features", ver)
    tables, hashes, stats = {}, {}, {}
    for pond, g in df.groupby("site"):
        pr = prepare_pond(g)
        grid = to_grid(pr, nominal)
        feats = compute_features(grid, fcfg, nominal)
        targets = make_targets(grid, fcfg, nominal)
        n = len(grid)
        meta = pd.DataFrame({"pond": pond, "grid_idx": np.arange(n), "ts_ist": grid["ts"], "ny_hour": grid["ny_hour"], "utc": grid["utc"],
                             "is_warmup": np.arange(n) < fcfg["warmup_steps"]})
        t = pd.concat([meta, feats, targets], axis=1)[grid["present"].to_numpy()].reset_index(drop=True)
        tables[pond], hashes[pond] = t, content_hash(t)
        stats[pond] = {"grid_points": int(n), "rows": int(len(t)), "DO_valid_pct": round(float(grid["DO"].notna().mean() * 100), 1),
                       "pH_valid_pct": round(float(grid["pH"].notna().mean() * 100), 1), "Temp_valid_pct": round(float(grid["Temp"].notna().mean() * 100), 1),
                       "DO_le_0.05_pct_of_valid": round(float((grid["DO"].dropna() <= 0.05).mean() * 100), 2),
                       "DO_lt_2_pct_of_valid": round(float((grid["DO"].dropna() < 2).mean() * 100), 1),
                       "first": str(grid["ts"].iloc[0]), "last": str(grid["ts"].iloc[-1])}
    mpath = Path(DATA_MOUNT, "manifests", f"bco_features_{ver}.json")
    if mpath.exists():
        same = json.loads(mpath.read_text(encoding="utf-8"))["content_hashes"] == hashes
        return {"feature_version": ver, "status": "reproduced_identical" if same else "MISMATCH", "stats": stats}
    out_dir.mkdir(parents=True, exist_ok=True)
    for pond, t in tables.items():
        t.to_parquet(out_dir / f"{pond.replace(' ', '_')}.parquet", index=False)
    mpath.write_text(json.dumps({"feature_version": ver, "code_git_sha": git_sha, "dataset": c["dataset"]["id"], "md5": c["dataset"]["md5"],
                                 "config": fcfg, "content_hashes": hashes, "stats": stats}, indent=2), encoding="utf-8")
    data_vol.commit()
    return {"feature_version": ver, "status": "written", "stats": stats,
            "n_columns": int(len(next(iter(tables.values())).columns))}


def _load_features(fv: str):
    import pandas as pd
    return pd.concat([pd.read_parquet(f) for f in sorted(Path(DATA_MOUNT, EXT, "features", fv).glob("*.parquet"))], ignore_index=True)


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def build_split(fv: str) -> dict:
    """Frozen split design from the contract, using the Phase 4 code. Write-once, hashed."""
    from aquatic_xai.splits.manifest import build_assignments, check_assignments, content_hash, gantt_text
    c = _cfg()
    data_vol.reload()
    scfg = _scfg(c)
    T = _load_features(fv)
    a, info = build_assignments(T, scfg)
    chk = check_assignments(a, info, scfg)
    h = content_hash(a)
    sv = "bsp-" + hashlib.sha256(json.dumps({"f": fv, "cfg": scfg, "code": "bco-split-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    d = Path(DATA_MOUNT, EXT, "splits", sv)
    mpath = Path(DATA_MOUNT, "manifests", f"bco_splits_{sv}.json")
    status = "reproduced_identical" if mpath.exists() and json.loads(mpath.read_text(encoding="utf-8"))["assignments_content_hash"] == h else "written"
    if not mpath.exists():
        d.mkdir(parents=True, exist_ok=True)
        a.to_parquet(d / "assignments.parquet", index=False)
        mpath.write_text(json.dumps({"split_version": sv, "feature_version": fv, "config": scfg, "assignments_content_hash": h, "info": info, "checks": chk}, indent=2), encoding="utf-8")
        data_vol.commit()
    counts = a[~a["is_warmup"]].groupby(["role"]).agg(rows=("pond", "size"), ponds=("pond", "nunique")).to_dict("index")
    return {"split_version": sv, "status": status, "hash": h, "info": info, "all_pass": chk["all_pass"], "checks": {k: v for k, v in chk.items() if k != "regimes"},
            "regimes": [{k: r[k] for k in ("regime", "train_rows", "eval_rows", "eval_ponds", "gap_hours", "pass")} for r in chk["regimes"]],
            "role_counts": counts, "gantt": gantt_text(a, info)}


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def integrity_checks(fv: str, sv: str) -> dict:
    """Leakage and alignment checks on the REAL 30-minute tables: all must pass before any model result is read."""
    import numpy as np
    import pandas as pd
    from aquatic_xai.alerts.labels import window_labels
    from aquatic_xai.data.external import prepare_pond, to_grid
    from aquatic_xai.features.daily import prefix_invariance_daily
    from aquatic_xai.features.leakage import identity_check, prefix_invariance, sample_origins
    from aquatic_xai.splits.manifest import content_hash
    c = _cfg()
    data_vol.reload()
    fcfg, nominal = _fcfg(c), c["grid"]["nominal_interval_min"]
    df = _raw_frame(c)
    T = _load_features(fv)
    a = pd.read_parquet(Path(DATA_MOUNT, EXT, "splits", sv, "assignments.parquet"))
    man = json.loads(Path(DATA_MOUNT, "manifests", f"bco_splits_{sv}.json").read_text(encoding="utf-8"))
    res = {"split_hash_matches_manifest": content_hash(a) == man["assignments_content_hash"]}
    thr = c["success_rules"]["alert"]["event"] and 2.0
    day = c["grid"]["steps_per_day"]
    Ws = [2, 6, 12]
    base_bad = base_n = tgt_bad = tgt_n = d_bad = d_n = lab_bad = lab_n = y_bad = y_n = 0
    max_diff = 0.0
    for pond, g in df.groupby("site"):
        pr = prepare_pond(g)
        grid = to_grid(pr, nominal)
        tab = T[T["pond"] == pond].reset_index(drop=True)
        rows = sample_origins(tab, c["leakage_samples_per_pond"] if "leakage_samples_per_pond" in c else 40, 20261020)
        r1 = prefix_invariance(grid, tab, fcfg, rows, nominal)
        base_bad, base_n, max_diff = base_bad + r1["mismatching_origins"], base_n + r1["origins_checked"], max(max_diff, r1["max_abs_diff"])
        sub = tab[["grid_idx", "DO_cur", "pH_cur", "Temp_cur"]]
        r2 = prefix_invariance_daily(sub, fcfg["horizons"], rows, day=day)
        d_bad, d_n = d_bad + r2["mismatching_origins"], d_n + r2["origins_checked"]
        # independent target re-derivation by UTC time lookup in the raw 10-minute series
        series = {v: pr.set_index("t")[v] for v in ("DO", "pH", "Temp")}
        for r in rows:
            t_utc = pd.Timestamp(tab.loc[r, "utc"], tz="UTC")
            for h in fcfg["horizons"]:
                for v in ("DO", "pH", "Temp"):
                    exp = series[v].get(t_utc + pd.Timedelta(minutes=nominal * h), np.nan)
                    got = tab.loc[r, f"y_{v}_h{h}"]
                    tgt_n += 1
                    tgt_bad += not ((np.isnan(exp) and np.isnan(got)) or exp == got)
        # alert labels: brute-force re-derivation and yesterday-window prefix invariance
        do = dict(zip(tab["grid_idx"], tab["DO_cur"].to_numpy(dtype=float)))
        from aquatic_xai.alerts.labels import add_alert_columns
        tab2 = add_alert_columns(tab, {"a": 2, "b": 6, "c": 12}, thr, day)
        for r in rows:
            gi = int(tab.loc[r, "grid_idx"])
            for W in Ws:
                v = np.array([do.get(gi + k, np.nan) for k in range(1, W + 1)], dtype=float)
                exp = 1.0 if np.nanmin(np.append(v, np.inf)) < thr else (0.0 if np.isfinite(v).sum() >= np.ceil(W / 2) else np.nan)
                got = tab2.loc[r, f"lab_W{W}"]
                lab_n += 1
                lab_bad += not ((np.isnan(exp) and np.isnan(got)) or exp == got)
                pre = tab.iloc[: r + 1][["grid_idx", "DO_cur"]]
                _, yd = window_labels(pre, W, thr, day)
                y_n += 1
                y_bad += not ((np.isnan(yd[-1]) and np.isnan(tab2.loc[r, f"ydaymin_W{W}"])) or yd[-1] == tab2.loc[r, f"ydaymin_W{W}"])
    res["feature_prefix_invariance"] = {"checked": base_n, "mismatches": base_bad, "max_abs_diff": max_diff}
    res["daily_prefix_invariance"] = {"checked": d_n, "mismatches": d_bad}
    res["target_rederivation"] = {"checked": tgt_n, "mismatches": tgt_bad}
    res["alert_label_rederivation"] = {"checked": lab_n, "mismatches": lab_bad}
    res["ydaymin_prefix_invariance"] = {"checked": y_n, "mismatches": y_bad}
    res["identity_check"] = identity_check(T, fcfg)
    res["all_pass"] = bool(res["split_hash_matches_manifest"] and base_bad == 0 and d_bad == 0 and tgt_bad == 0 and lab_bad == 0 and y_bad == 0
                           and res["identity_check"]["max_equal_fraction"] < 0.99 and man["checks"]["all_pass"])
    return res


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout[-300:] + r.stderr[-300:]


# ----------------------------------------------------------------------------------------------- stage 2
def _stage2_data(sv: str, fv: str):
    import pandas as pd
    from aquatic_xai.alerts.labels import add_alert_columns
    from aquatic_xai.features.daily import daily_features
    k = (sv, fv)
    if k not in _CACHE:
        data_vol.reload()
        c = _cfg()
        fc = _fcfg(c)
        feats = _load_features(fv)
        a = pd.read_parquet(Path(DATA_MOUNT, EXT, "splits", sv, "assignments.parquet"))
        T = feats.merge(a[["pond", "grid_idx", "window", "role", "fold", "block_day"]], on=["pond", "grid_idx"], how="inner", validate="one_to_one")
        assert len(T) == len(feats) == len(a)
        parts = [daily_features(g, fc["horizons"], day=c["grid"]["steps_per_day"]) for _, g in T.groupby("pond", sort=False)]
        T = pd.concat([T, pd.concat(parts).loc[T.index]], axis=1)
        T = add_alert_columns(T, {"a": 2, "b": 6, "c": 12}, 2.0, c["grid"]["steps_per_day"])
        man = json.loads(Path(DATA_MOUNT, "manifests", f"bco_splits_{sv}.json").read_text(encoding="utf-8"))
        _CACHE[k] = (T, man["info"], man["config"]["cv_folds"], a, man)
    return _CACHE[k]


ANCHORS = {1: "persistence", 2: "persistence", 12: "yesterday"}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def forecast_task(regime: str, var: str, h: int, sv: str, fv: str):
    from aquatic_xai.experiments.run_anchored import run_task_anchored
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    c, m = _cfg(), _yaml("models.yaml")
    T, info, k, _, _ = _stage2_data(sv, fv)
    fc = _fcfg(c)
    acfg = {"anchors": ANCHORS, "seeds": m["models"]["seeds"]}
    metrics, preds = run_task_anchored(T, info, k, regime, var, h, feature_specs(fc), daily_specs(fc["horizons"]), m["models"]["lightgbm"], acfg,
                                       c["grid"]["steps_per_day"], m["evaluation"]["low_quantile"], versions=(False,))
    buf = io.BytesIO()
    preds.to_parquet(buf, index=False)
    return metrics, buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def alert_task(regime: str, W: int, sv: str, fv: str) -> bytes:
    from aquatic_xai.alerts.run import run_alert_task
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    c, m = _cfg(), _yaml("models.yaml")
    T, info, k, _, _ = _stage2_data(sv, fv)
    fc = _fcfg(c)
    out = run_alert_task(T, info, k, regime, W, feature_specs(fc), daily_specs(fc["horizons"]), m["models"]["lightgbm"], m["models"]["seeds"],
                         slope_col=f"DO_slope{fc['slope_window']}", step_min=c["grid"]["nominal_interval_min"])
    buf = io.BytesIO()
    out.to_parquet(buf, index=False)
    return buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_stage2(git_sha: str, sv: str, fv: str) -> dict:
    c = _cfg()
    exp_id = "exp-" + hashlib.sha256(json.dumps({"s": sv, "f": fv, "cfg": c, "models": _yaml("models.yaml")["models"], "code": "bco-r-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    if (out / "manifest.json").exists():
        return {"experiment_id": exp_id, "status": "already_exists"}
    regs = ["dev_future_seen_ponds"] + [f"dev_future_unseen_fold{k}" for k in range(4)]
    fargs = [(r, v, h, sv, fv) for r in regs for v in ("DO", "pH", "Temp") for h in (1, 2, 12)]
    aargs = [(r, W, sv, fv) for r in regs for W in (2, 6, 12)]
    fres = list(forecast_task.starmap(fargs, order_outputs=True))
    ares = list(alert_task.starmap(aargs, order_outputs=True))
    (out / "preds").mkdir(parents=True, exist_ok=True)
    (out / "alerts").mkdir(parents=True, exist_ok=True)
    allm = []
    for (r, v, h, _, _), (metrics, blob) in zip(fargs, fres):
        (out / "preds" / f"{r}__{v}__h{h}.parquet").write_bytes(blob)
        allm += metrics
    for (r, W, _, _), blob in zip(aargs, ares):
        (out / "alerts" / f"{r}__W{W}.parquet").write_bytes(blob)
    secs = sum(m.get("seconds", 0) for m in allm if m["model"] == "_task")
    (out / "metrics.json").write_text(json.dumps(allm, indent=1), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"experiment_id": exp_id, "code_git_sha": git_sha, "split_version": sv, "feature_version": fv, "config": c,
                                                   "n_forecast_tasks": len(fargs), "n_alert_tasks": len(aargs), "task_seconds_total": round(secs, 1),
                                                   "note": "validation-side only; sealed pond and test window not used"}, indent=2), encoding="utf-8")
    artifact_vol.commit()
    return {"experiment_id": exp_id, "status": "written", "task_seconds_total": round(secs, 1)}


@app.function(image=image, volumes=VOLUMES, timeout=900)
def repro_check(sv: str, fv: str) -> dict:
    import numpy as np
    import pandas as pd
    a = forecast_task.remote("dev_future_unseen_fold1", "pH", 12, sv, fv)
    b = forecast_task.remote("dev_future_unseen_fold1", "pH", 12, sv, fv)
    da, db = pd.read_parquet(io.BytesIO(a[1])), pd.read_parquet(io.BytesIO(b[1]))
    d1 = {x: float(np.nanmax(np.abs(da[x].to_numpy() - db[x].to_numpy()))) for x in da.columns if x.startswith("ae_")}
    aa = pd.read_parquet(io.BytesIO(alert_task.remote("dev_future_unseen_fold1", 12, sv, fv)))
    bb = pd.read_parquet(io.BytesIO(alert_task.remote("dev_future_unseen_fold1", 12, sv, fv)))
    return {"forecast_max_abs_diff": d1, "alert_max_abs_diff": float(np.max(np.abs(aa["p_model"].to_numpy() - bb["p_model"].to_numpy()))),
            "identical_rows": bool(da[["pond", "grid_idx"]].equals(db[["pond", "grid_idx"]]))}


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def analyze(exp_id: str) -> str:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import average_precision_score as aps
    from aquatic_xai.alerts.calibrate import brier, choose_level, evaluate_level, false_alarm_flags, fit_isotonic
    from aquatic_xai.alerts.evaluate import ap_ci
    from aquatic_xai.alerts.labels import episode_onsets
    from aquatic_xai.experiments.evaluate import improvement_ci, mean_ci
    from aquatic_xai.uncertainty.conformal import conformal_q
    data_vol.reload()
    artifact_vol.reload()
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    c = man["config"]
    sv, fv = man["split_version"], man["feature_version"]
    T = _stage2_data(sv, fv)[0]
    nyh = T.set_index(["pond", "grid_idx"])["ny_hour"]
    fmeta = json.loads(Path(DATA_MOUNT, "manifests", f"bco_features_{fv}.json").read_text(encoding="utf-8"))
    sr = c["success_rules"]
    hl = {1: "30 min", 2: "1 h", 12: "6 h"}
    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    grp = lambda r: "seen" if r == "dev_future_seen_ponds" else "unseen"
    frames = {}
    for f in sorted((out / "preds").glob("*.parquet")):
        r, v, h = f.stem.split("__")
        frames.setdefault((grp(r), v, int(h[1:])), []).append(pd.read_parquet(f).assign(fold=r))
    D = {k: pd.concat(v, ignore_index=True) for k, v in frames.items()}
    B, seed0 = 2000, 20261113
    ctr = [0]

    def nxt():
        ctr[0] += 1
        return seed0 + ctr[0]

    L = [f"# Phase 1b-R results: method replication on BCO-DMO 988873 (salt-marsh ponds), experiment `{exp_id}`", "",
         f"- Contract `configs/replication_bco.yaml` (frozen before any code ran). Split `{sv}`, features `{fv}`, code commit `{man['code_git_sha'][:12]}`.",
         "- Validation-side only. Held-out ponds: Drum, Long Reach, Ring East, White (one pond per fold). **The sealed pond (Shark) and the test window were not used.**",
         "- Dataset limits: tidal salt marsh, not managed aquaculture; 30-minute subsample of a 10-minute series; oxygen converted from umol/kg (approximate density). Intervals are 99% blocked bootstrap (blocks = pond x day).", "",
         "## 0. Data facts that shape every result below (per pond, valid readings on the 30-minute grid)", "",
         "| pond | oxygen valid | pH valid | temperature valid | oxygen <= 0.05 mg/L (share of valid) | oxygen < 2 mg/L (share of valid) |", "|---|---|---|---|---|---|"]
    for p, s in fmeta["stats"].items():
        L.append(f"| {p} | {s['DO_valid_pct']}% | {s['pH_valid_pct']}% | {s['Temp_valid_pct']}% | {s['DO_le_0.05_pct_of_valid']}% | {s['DO_lt_2_pct_of_valid']}% |")
    L += ["", "Near-zero oxygen is common (about 12% to 18% of valid readings). Per the contract these values are kept as valid and no run with them masked was made.", ""]

    # ---- A. forecasts
    cols = [(g, h) for g in ("seen", "unseen") for h in (1, 2, 12)]
    head = "| model | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |\n|---|" + "---|" * len(cols)
    L.append("## A. Forecast accuracy: average miss (MAE) with 99% intervals")
    for v in ("DO", "pH", "Temp"):
        L += ["", f"### {v} ({unit[v]})", "", head]
        for m in ("persistence", "seasonal_naive", "anch_blind"):
            L.append(f"| {m} | " + " | ".join(_fmt(mean_ci(D[(g, v, h)], f"ae_{m}", B, nxt(), 99)) for g, h in cols) + " |")
    L += ["", "### Pre-registered success rule per cell (held-out ponds): improvement over BOTH simple guesses, lower end of the 99% interval must be > 0", "",
          "| target | ahead | vs 'same as now' | vs 'same time yesterday' | verdict |", "|---|---|---|---|---|"]
    verdict = {}
    for v in ("DO", "pH", "Temp"):
        for h in (1, 2, 12):
            d = D[("unseen", v, h)]
            a_, b_ = improvement_ci(d, "ae_anch_blind", "ae_persistence", B, nxt(), 99), improvement_ci(d, "ae_anch_blind", "ae_seasonal_naive", B, nxt(), 99)
            ok = a_[1] > 0 and b_[1] > 0
            verdict[(v, h)] = ok
            L.append(f"| {v} | {hl[h]} | {_fmt(a_, pct=True)} | {_fmt(b_, pct=True)} | {'PASS' if ok else 'fail'} |")
    n_pass = sum(verdict.values())
    six_h = any(verdict[(v, 12)] for v in ("DO", "pH", "Temp"))
    repl = n_pass >= 3 and six_h
    L += ["", f"**{n_pass} of 9 cells pass.** A 6 h cell passes: {six_h}. **Pre-registered verdict on 'the method replicates': {'YES' if repl else 'NO'}** (needs at least 3 of 9 cells and at least one 6 h cell)."]

    # ---- B. ranges
    L += ["", "## B. Forecast ranges (split-conformal, 90% target), held-out ponds", "",
          "Centre of each range = the model if its cell passed, otherwise the better simple guess (same mechanical rule as Phase 5b). Calibration = the other three held-out ponds.", "",
          "| target | ahead | centre | coverage (plain) | half-width | day / night / low-value coverage | coverage (day/night variant) | day / night / low | per-pond coverage (min-max) | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    folds = [f"dev_future_unseen_fold{k}" for k in range(4)]
    n_r = 0
    for v in ("DO", "pH", "Temp"):
        for h in (1, 2, 12):
            d = D[("unseen", v, h)]
            if verdict[(v, h)]:
                pick = "anch_blind"
            else:
                pm = mean_ci(d, "ae_persistence", B, 1, 99)[0]
                sm = mean_ci(d.dropna(subset=["ae_seasonal_naive"]), "ae_seasonal_naive", B, 1, 99)[0]
                pick = "persistence" if pm <= sm else "seasonal_naive"
            col = f"ae_{pick}"
            rows, per, widths = [], [], []
            for k in folds:
                cal, ev = d[d["fold"] != k].dropna(subset=[col]), d[d["fold"] == k].dropna(subset=[col]).copy()
                hr = lambda x: np.array([nyh.get((p, g), np.nan) for p, g in zip(x["pond"], x["grid_idx"])])
                cal = cal.assign(day=(hr(cal) >= 6) & (hr(cal) < 18))
                ev["day"] = (hr(ev) >= 6) & (hr(ev) < 18)
                q = conformal_q(cal[col].to_numpy(), 0.10)
                qd, qn = conformal_q(cal[cal["day"]][col].to_numpy(), 0.10), conformal_q(cal[~cal["day"]][col].to_numpy(), 0.10)
                ev["cov"] = (ev[col] <= q).astype(float)
                ev["cov_dn"] = (ev[col] <= np.where(ev["day"], qd, qn)).astype(float)
                ev["low"] = ev["y"] <= ev["y_train_low"]
                rows.append(ev)
                per.append(float(ev["cov"].mean()))
                widths.append(q)
            E = pd.concat(rows, ignore_index=True)
            cov = mean_ci(E, "cov", B, nxt(), 99)
            cd = lambda cc: (E[E["day"]][cc].mean(), E[~E["day"]][cc].mean(), E[E["low"]][cc].mean())
            a3, b3 = cd("cov"), cd("cov_dn")
            dn = E["cov_dn"].mean()
            ok_p = 0.87 <= cov[0] <= 0.93 and min(a3) >= 0.85
            ok_d = 0.87 <= dn <= 0.93 and min(b3) >= 0.85
            vd = "PASS (plain)" if ok_p else ("PASS (day/night)" if ok_d else "fail")
            n_r += vd != "fail"
            f3 = lambda t: " / ".join(f"{x*100:.0f}%" for x in t)
            L.append(f"| {v} ({unit[v]}) | {hl[h]} | {pick} | {cov[0]*100:.1f}% [{cov[1]*100:.1f}, {cov[2]*100:.1f}] | ±{np.mean(widths):.3f} | {f3(a3)} | {dn*100:.1f}% | {f3(b3)} | {min(per)*100:.0f}%-{max(per)*100:.0f}% | {vd} |")
    L += ["", f"**{n_r} of 9 cells pass** the pre-registered coverage rule."]

    # ---- C. alert
    thr = 2.0
    Wn = {2: "1 h", 6: "3 h", 12: "6 h"}
    A = {}
    for f in sorted((out / "alerts").glob("*.parquet")):
        r, w = f.stem.split("__")
        A.setdefault((grp(r), int(w[1:])), []).append(pd.read_parquet(f).assign(fold=r))
    A = {k: pd.concat(v, ignore_index=True) for k, v in A.items()}
    L += ["", f"## C. Low-oxygen early warning (any reading below {thr} mg/L within the next window), held-out ponds", "",
          "| window | event rate | model AP | yesterday AP | trend AP | level AP | model minus each baseline (99% interval) | verdict |", "|---|---|---|---|---|---|---|---|"]
    n_a = 0
    for W in (2, 6, 12):
        d = A[("unseen", W)]
        r = ap_ci(d, "y", ["p_model", "s_yday", "s_trend", "s_level"], 1000, seed0 + W, 99)
        dd = r["diff"]
        ok = all(dd[s][1] > 0 for s in dd)
        n_a += ok
        L.append(f"| {Wn[W]} | {d['y'].mean()*100:.1f}% | {r['ap']['p_model']:.3f} | {r['ap']['s_yday']:.3f} | {r['ap']['s_trend']:.3f} | {r['ap']['s_level']:.3f} | "
                 + "; ".join(f"vs {n}: {dd[s][0]:+.3f} [{dd[s][1]:+.3f}, {dd[s][2]:+.3f}]" for s, n in (("s_yday", "yesterday"), ("s_trend", "trend"), ("s_level", "level"))) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{n_a} of 3 windows pass** the pre-registered rule (all three baselines, 99%)."]
    L += ["", "### Calibration (isotonic fitted on the other three ponds)", "", "| window | Brier raw | Brier calibrated | bins (calibrated -> actual, n) | criterion |", "|---|---|---|---|---|"]
    cal_ok = 0
    cal_frames = {}
    for W in (2, 6, 12):
        d = A[("unseen", W)]
        parts = []
        for k in folds:
            others = d[d["fold"] != k]
            iso = fit_isotonic(others["p_model"].to_numpy(), others["y"].to_numpy())
            x = d[d["fold"] == k].copy()
            x["p_cal"] = iso.predict(x["p_model"].to_numpy())
            parts.append(x)
        D2 = pd.concat(parts, ignore_index=True)
        cal_frames[W] = D2
        bins = pd.cut(D2["p_cal"], [0, .1, .3, .5, .7, .9, 1.0001], include_lowest=True)
        g = D2.groupby(bins, observed=False).agg(n=("y", "size"), rate=("y", "mean"), pm=("p_cal", "mean"))
        big = g[g["n"] >= 100]
        ok = brier(D2["p_cal"], D2["y"]) < brier(D2["p_model"], D2["y"]) and bool(((big["pm"] - big["rate"]).abs() <= 0.10).all())
        cal_ok += ok
        L.append(f"| {Wn[W]} | {brier(D2['p_model'], D2['y']):.4f} | {brier(D2['p_cal'], D2['y']):.4f} | " + "; ".join(f"{x.pm*100:.0f}% -> {x.rate*100:.0f}% ({int(x.n)})" for x in g.itertuples() if x.n) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{cal_ok} of 3 windows pass** the calibration criterion."]
    # decision rule, 6 h
    W = 12
    onsets = {p: episode_onsets(g[["grid_idx", "DO_cur"]], thr, 12) for p, g in T.groupby("pond", sort=False)}
    d = cal_frames[W]
    fa_parts, pooled = [], {"m": [0, 0, []], "b": [0, 0, []]}
    L += ["", "### Decision rule (6 h): alert level chosen on the other ponds for >= 80% episode recall, then applied to the held-out pond", "",
          "| held-out pond fold | model recall | model false-alarm days | baseline ('same window yesterday') recall | baseline false-alarm days |", "|---|---|---|---|---|"]
    for k in folds:
        cal, ev = d[d["fold"] != k], d[d["fold"] == k]
        tm, _ = choose_level(cal, onsets, "p_model", 0.8, 2, 12, 0.5)
        tb, _ = choose_level(cal, onsets, "s_yday", 0.8, 2, 12, 0.5)
        sm, sb = evaluate_level(ev, onsets, "p_model", tm, 2, 12, 0.5), evaluate_level(ev, onsets, "s_yday", tb, 2, 12, 0.5)
        fa_parts.append(false_alarm_flags(ev, "p_model", tm).merge(false_alarm_flags(ev, "s_yday", tb), on=["pond", "block_day"], suffixes=("_m", "_b")))
        for key, st in (("m", sm), ("b", sb)):
            pooled[key][0] += st["episodes"]
            pooled[key][1] += st["caught"]
            pooled[key][2] += st["leads"]
        L.append(f"| {k[-5:]} | {sm['caught']}/{sm['episodes']} | {sm['false_alarm_pond_days']}/{sm['pond_days']} | {sb['caught']}/{sb['episodes']} | {sb['false_alarm_pond_days']}/{sb['pond_days']} |")
    FA = pd.concat(fa_parts, ignore_index=True)
    FA["diff"] = FA["fa_m"] - FA["fa_b"]
    dci = mean_ci(FA, "diff", B, nxt(), 99)
    rm, rb = pooled["m"][1] / max(pooled["m"][0], 1), pooled["b"][1] / max(pooled["b"][0], 1)
    ok = dci[2] < 0 and rm >= rb - 0.05
    L += ["", f"Pooled: model catches {pooled['m'][1]}/{pooled['m'][0]} episodes ({rm*100:.0f}%), median warning {np.median(pooled['m'][2]) if pooled['m'][2] else float('nan'):.2f} h, false-alarm share {FA['fa_m'].mean()*100:.0f}% of pond-days. "
              f"Baseline catches {pooled['b'][1]}/{pooled['b'][0]} ({rb*100:.0f}%), median warning {np.median(pooled['b'][2]) if pooled['b'][2] else float('nan'):.2f} h, false-alarm share {FA['fa_b'].mean()*100:.0f}%.",
          f"False-alarm share, model minus baseline: **{dci[0]*100:+.1f} points** (99% interval {dci[1]*100:+.1f} to {dci[2]*100:+.1f}, n={len(FA)} pond-days). **Pre-registered verdict: {'PASS' if ok else 'FAIL'}.**"]

    # ---- summary
    L += ["", "## Summary against the pre-registered rules", "",
          f"| rule | result |", "|---|---|",
          f"| Forecast cells beating both simple guesses (99%) | {n_pass} of 9; method replicates: **{'YES' if repl else 'NO'}** |",
          f"| Range coverage rule | {n_r} of 9 cells pass |",
          f"| Alert beats 3 baselines (AP, 99%) | {n_a} of 3 windows |",
          f"| Alert calibration criterion | {cal_ok} of 3 windows |",
          f"| Alert false-alarm decision rule | {'PASS' if ok else 'FAIL'} |"]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


def _fmt(t, pct: bool = False, digits: int = 3) -> str:
    import numpy as np
    est, lo, hi, _ = t
    if np.isnan(est):
        return "n/a"
    return f"{est*100:+.1f}% [{lo*100:+.1f}, {hi*100:+.1f}]" if pct else f"{est:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


@app.function(image=image, volumes=VOLUMES, timeout=120)
def bco_versions() -> tuple[str, str]:
    data_vol.reload()
    f = sorted(Path(DATA_MOUNT, "manifests").glob("bco_features_*.json"), key=lambda p: p.stat().st_mtime)
    s = sorted(Path(DATA_MOUNT, "manifests").glob("bco_splits_*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(s[-1].read_text(encoding="utf-8"))["split_version"], json.loads(f[-1].read_text(encoding="utf-8"))["feature_version"]


@app.local_entrypoint()
def stage2(git_sha: str = "unknown"):
    sv, fv = bco_versions.remote()
    res = run_stage2.remote(git_sha, sv, fv)
    print("RUN:", json.dumps(res))
    if res["status"] == "written":
        print("REPRO:", json.dumps(repro_check.remote(sv, fv)))
    report = analyze.remote(res["experiment_id"])
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{res['experiment_id']}_replication_bco.md").write_text(report, encoding="utf-8")
    print(report)


@app.local_entrypoint()
def reanalyze(exp_id: str):
    report = analyze.remote(exp_id)
    Path(f"docs/experiments/{exp_id}_replication_bco.md").write_text(report, encoding="utf-8")
    print(report)


@app.local_entrypoint()
def stage1(git_sha: str = "unknown"):
    print(tests_remote.remote())
    d = build_data.remote(git_sha)
    print("DATA:", json.dumps({k: v for k, v in d.items() if k != "stats"}))
    for p, s in d["stats"].items():
        print(" ", p, json.dumps(s))
    if d["status"] == "MISMATCH":
        raise SystemExit("STOP: rebuilt features differ from the stored version")
    s = build_split.remote(d["feature_version"])
    print("SPLIT:", json.dumps({k: v for k, v in s.items() if k not in ("gantt", "regimes", "role_counts")}))
    print(s["gantt"])
    print("role counts:", json.dumps(s["role_counts"]))
    for r in s["regimes"]:
        print("  ", json.dumps(r))
    chk = integrity_checks.remote(d["feature_version"], s["split_version"])
    print("INTEGRITY:", json.dumps(chk))
    print("STAGE1", "PASS" if chk["all_pass"] else "FAIL")
