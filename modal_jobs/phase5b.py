"""Phase 5b: one anchored-residual LightGBM (quality-blind / quality-aware), validation-side only. Rules in configs/anchored.yaml.

    modal run -m modal_jobs.phase5b::main --git-sha <sha>
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image

_CACHE: dict = {}
PHASE5_EXP = "exp-a0a394b0d781"


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _latest(glob: str, key: str) -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob(glob), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))[key]


def _data(split_version: str, feature_version: str):
    """Phase 3 table + split assignments + Phase 5b daily features."""
    import pandas as pd
    from aquatic_xai.features.daily import daily_features
    k = (split_version, feature_version)
    if k not in _CACHE:
        data_vol.reload()
        feats = pd.concat([pd.read_parquet(f) for f in sorted(Path(DATA_MOUNT, "features", feature_version).glob("*.parquet"))],
                          ignore_index=True)
        a = pd.read_parquet(Path(DATA_MOUNT, "splits", split_version, "assignments.parquet"))
        T = feats.merge(a[["pond", "grid_idx", "window", "role", "fold", "block_day"]], on=["pond", "grid_idx"], how="inner", validate="one_to_one")
        assert len(T) == len(feats) == len(a)
        hs = _yaml("features.yaml")["features"]["horizons"]
        parts = [daily_features(g, hs) for _, g in T.groupby("pond", sort=False)]
        T = pd.concat([T, pd.concat(parts).loc[T.index]], axis=1)
        man = json.loads(Path(DATA_MOUNT, "manifests", f"splits_{split_version}.json").read_text(encoding="utf-8"))
        _CACHE[k] = (T, man["info"], man["config"]["cv_folds"], a, man)
    return _CACHE[k]


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def run_task_remote(regime: str, var: str, h: int, split_version: str, feature_version: str) -> tuple[list, bytes]:
    from aquatic_xai.experiments.run_anchored import run_task_anchored
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    T, info, k, _, _ = _data(split_version, feature_version)
    m = _yaml("models.yaml")
    f = _yaml("features.yaml")["features"]
    metrics, preds = run_task_anchored(T, info, k, regime, var, h, feature_specs(f), daily_specs(f["horizons"]), m["models"]["lightgbm"],
                                       _yaml("anchored.yaml")["anchored"], m["models"]["seasonal_steps"], m["evaluation"]["low_quantile"])
    buf = io.BytesIO()
    preds.to_parquet(buf, index=False)
    return metrics, buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def checks(split_version: str, feature_version: str) -> dict:
    """Split frozen? Daily features leak-free on real tables?"""
    import numpy as np
    from aquatic_xai.features.daily import prefix_invariance_daily
    from aquatic_xai.splits.manifest import content_hash
    T, _, _, a, man = _data(split_version, feature_version)
    cfg = _yaml("anchored.yaml")["anchored"]["leakage"]
    hs = _yaml("features.yaml")["features"]["horizons"]
    res = {"assignments_hash_now": content_hash(a), "assignments_hash_manifest": man["assignments_content_hash"]}
    res["split_identical"] = res["assignments_hash_now"] == res["assignments_hash_manifest"]
    rng, tot, bad, mx, nf = np.random.RandomState(cfg["seed"]), 0, 0, 0.0, 0
    for pond, g in T.groupby("pond", sort=False):
        g = g[["grid_idx", "DO_cur", "pH_cur", "Temp_cur", "is_warmup"]]
        ok = g.index[~g["is_warmup"]].to_numpy()
        rows = np.sort(rng.choice(ok, size=min(cfg["samples_per_pond"], len(ok)), replace=False))
        r = prefix_invariance_daily(g, hs, rows)
        tot, bad, mx, nf = tot + r["origins_checked"], bad + r["mismatching_origins"], max(mx, r["max_abs_diff"]), r["features_checked"]
    res["daily_prefix_invariance"] = {"origins_checked": tot, "features_checked": nf, "mismatching_origins": bad, "max_abs_diff": mx}
    return res


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_phase5b(git_sha: str, split_version: str, feature_version: str) -> dict:
    import hashlib
    import lightgbm
    cfg = {"anchored": _yaml("anchored.yaml"), "models": _yaml("models.yaml")}
    exp_id = "exp-" + hashlib.sha256(json.dumps({"s": split_version, "f": feature_version, "cfg": cfg, "code": "p5b-v1+daily-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    if (out / "manifest.json").exists():
        return {"experiment_id": exp_id, "status": "already_exists"}
    ac, ev = cfg["anchored"]["anchored"], cfg["models"]["evaluation"]
    args = [(r, v, h, split_version, feature_version) for r in ac["regimes"] for v in ev["variables"] for h in ev["horizons"]]
    results = list(run_task_remote.starmap(args, order_outputs=True))
    (out / "preds").mkdir(parents=True, exist_ok=True)
    allm = []
    for (r, v, h, _, _), (metrics, blob) in zip(args, results):
        (out / "preds" / f"{r}__{v}__h{h}.parquet").write_bytes(blob)
        allm += metrics
    secs = sum(m.get("seconds", 0) for m in allm if m["model"] == "_task")
    (out / "metrics.json").write_text(json.dumps(allm, indent=1), encoding="utf-8")
    tmp = out / "manifest.json.part"
    tmp.write_text(json.dumps({"experiment_id": exp_id, "code_git_sha": git_sha, "split_version": split_version, "feature_version": feature_version,
                               "daily_features": "daily-v1", "config": cfg, "versions": {"lightgbm": lightgbm.__version__},
                               "n_tasks": len(args), "task_seconds_total": round(secs, 1), "phase5_experiment": PHASE5_EXP,
                               "note": "validation-side only; FINAL regimes not run"}, indent=2), encoding="utf-8")
    tmp.replace(out / "manifest.json")
    artifact_vol.commit()
    return {"experiment_id": exp_id, "status": "written", "n_tasks": len(args), "task_seconds_total": round(secs, 1)}


@app.function(image=image, volumes=VOLUMES, timeout=900)
def repro_check(split_version: str, feature_version: str) -> dict:
    import numpy as np
    import pandas as pd
    a = run_task_remote.remote("dev_future_seen_ponds", "pH", 24, split_version, feature_version)
    b = run_task_remote.remote("dev_future_seen_ponds", "pH", 24, split_version, feature_version)
    da, db = pd.read_parquet(io.BytesIO(a[1])), pd.read_parquet(io.BytesIO(b[1]))
    cols = [c for c in da.columns if c.startswith("ae_")]
    return {"max_abs_diff": {c: float(np.nanmax(np.abs(da[c].to_numpy() - db[c].to_numpy()))) for c in cols},
            "identical_rows": bool(da[["pond", "grid_idx"]].equals(db[["pond", "grid_idx"]]))}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def analyze(exp_id: str) -> str:
    import numpy as np
    import pandas as pd
    from aquatic_xai.experiments.evaluate import diff_ci, fmt, improvement_ci, mean_ci
    artifact_vol.reload()
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    metrics = pd.DataFrame(json.loads((out / "metrics.json").read_text(encoding="utf-8")))
    ac = man["config"]["anchored"]["anchored"]
    ev = man["config"]["models"]["evaluation"]
    B, seed0, lv = ac["bootstrap"]["B"], ac["bootstrap"]["seed"], ac["ci_level"]
    grp = lambda r: "seen" if r == "dev_future_seen_ponds" else "unseen"
    frames, p5 = {}, {}
    for f in sorted((out / "preds").glob("*.parquet")):
        r, v, h = f.stem.split("__")
        frames.setdefault((grp(r), v, int(h[1:])), []).append(pd.read_parquet(f))
        q = Path(ARTIFACT_MOUNT, "experiments", man["phase5_experiment"], "preds", f.name)
        p5.setdefault((grp(r), v, int(h[1:])), []).append(pd.read_parquet(q, columns=["pond", "grid_idx", "ae_lgbm_blind", "ae_lgbm_aware"]))
    D = {k: pd.concat(v, ignore_index=True) for k, v in frames.items()}
    P5 = {k: pd.concat(v, ignore_index=True) for k, v in p5.items()}
    H, V = ev["horizons"], ev["variables"]
    hl = {1: "15 min", 4: "1 h", 24: "6 h"}
    ctr = [0]

    def nxt():
        ctr[0] += 1
        return seed0 + ctr[0]

    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    cols = [(g, h) for g in ("seen", "unseen") for h in H]
    head = "| model | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |\n|---|" + "---|" * len(cols)
    L = [f"# Phase 5b results, experiment `{exp_id}`", "",
         f"- Split `{man['split_version']}` (unchanged), Phase 3 features `{man['feature_version']}` + daily-pattern features `daily-v1`, code commit `{man['code_git_sha'][:12]}`",
         f"- One anchored-residual LightGBM, fixed Phase 5 settings, no tuning, one round. Seeds {ac['seeds']}. Intervals are **{lv}%** blocked-bootstrap (blocks = pond x day).",
         f"- Compute: {man['task_seconds_total']} container-seconds, 2 CPU cores each, no GPU. **Validation-side only; sealed test not used.**",
         f"- Pre-registered success rule: {ac['success_rule']}.", f"- Recommendation rule: {ac['recommendation_rule']}.", ""]
    L.append("## 1. Average miss (MAE, native units) with intervals")
    for v in V:
        L += ["", f"### {v} ({unit[v]})", "", head]
        for m in ("persistence", "seasonal_naive", "anch_blind", "anch_aware"):
            L.append(f"| {m} | " + " | ".join(fmt(mean_ci(D[(g, v, h)], f"ae_{m}", B, nxt(), lv)) for g, h in cols) + " |")

    L += ["", "## 2. Success rule on unseen ponds (improvement over each simple guess; lower end of interval must be > 0 for BOTH)", "",
          "| target | ahead | version | vs 'same as now' | vs 'same time yesterday' | verdict |", "|---|---|---|---|---|---|"]
    verdict = {}
    for v in V:
        for h in H:
            d = D[("unseen", v, h)]
            for m in ("anch_blind", "anch_aware"):
                a, b = improvement_ci(d, f"ae_{m}", "ae_persistence", B, nxt(), lv), improvement_ci(d, f"ae_{m}", "ae_seasonal_naive", B, nxt(), lv)
                ok = a[1] > 0 and b[1] > 0
                verdict[(v, h, m)] = ok
                L.append(f"| {v} | {hl[h]} | {m} | {fmt(a, pct=True)} | {fmt(b, pct=True)} | {'PASS' if ok else 'fail'} |")

    L += ["", "## 3. Does quality information help? (aware minus blind MAE, unseen; negative = aware better)", "",
          "| target | " + " | ".join(hl[h] for h in H) + " |", "|---|" + "---|" * len(H)]
    h1 = {}
    for v in V:
        cells = []
        for h in H:
            c = diff_ci(D[("unseen", v, h)], "ae_anch_aware", "ae_anch_blind", B, nxt(), lv)
            h1[(v, h)] = c[2] < 0
            cells.append(fmt(c, digits=4))
        L.append(f"| {v} | " + " | ".join(cells) + " |")

    L += ["", "## 4. What each cell should use (applying the recommendation rule mechanically)", "",
          "| target | ahead | use | simple-guess MAEs (now / yesterday) | chosen MAE |", "|---|---|---|---|---|"]
    for v in V:
        for h in H:
            d = D[("unseen", v, h)]
            pm, sm = mean_ci(d, "ae_persistence", B, 1, lv)[0], mean_ci(d.dropna(subset=["ae_seasonal_naive"]), "ae_seasonal_naive", B, 1, lv)[0]
            if verdict[(v, h, "anch_blind")]:
                use, col = "anchored LightGBM, quality-blind", "ae_anch_blind"
            elif verdict[(v, h, "anch_aware")] and h1[(v, h)]:
                use, col = "anchored LightGBM, quality-aware", "ae_anch_aware"
            else:
                use, col = ("'same as now'", "ae_persistence") if pm <= sm else ("'same time yesterday'", "ae_seasonal_naive")
            L.append(f"| {v} | {hl[h]} | {use} | {pm:.3f} / {sm:.3f} | {mean_ci(d, col, B, 1, lv)[0]:.3f} |")

    L += ["", "## 5. Against the Phase 5 LightGBM (level model), same rows; positive = anchored is better", "",
          "| target | version | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |", "|---|---|" + "---|" * len(cols)]
    for v in V:
        for m, pc in (("anch_blind", "ae_lgbm_blind"), ("anch_aware", "ae_lgbm_aware")):
            cells = []
            for g, h in cols:
                j = D[(g, v, h)][["pond", "grid_idx", "block_day", f"ae_{m}"]].merge(P5[(g, v, h)][["pond", "grid_idx", pc]], on=["pond", "grid_idx"])
                cells.append(fmt(improvement_ci(j, f"ae_{m}", pc, B, nxt(), lv), pct=True))
            L.append(f"| {v} | {m} | " + " | ".join(cells) + " |")

    L += ["", "## 6. Hard cases: bottom 10% of training values, unseen ponds (MAE, with n)", "",
          "| target | model | " + " | ".join(hl[h] for h in H) + " |", "|---|---|" + "---|" * len(H)]
    for v in V:
        for m in ("persistence", "seasonal_naive", "anch_blind", "anch_aware"):
            cells = []
            for h in H:
                d = D[("unseen", v, h)]
                d = d[d["y"] <= d["y_train_low"]]
                cells.append(f"{fmt(mean_ci(d, f'ae_{m}', B, nxt(), lv))} (n={len(d)})")
            L.append(f"| {v} | {m} | " + " | ".join(cells) + " |")

    t = metrics[(metrics["model"] == "_task") & (metrics["h"] == 24)]
    fr = t.groupby("var").apply(lambda x: (np.average(x["fallback_rate_eval"], weights=x["n_eval"]), np.average(x["fallback_rate_train"], weights=x["n_eval"])))
    L += ["", "## 7. How often 'yesterday' was missing at 6 h (anchor fell back to 'same as now')", "",
          "| target | evaluation rows | training rows |", "|---|---|---|"] + [f"| {k} | {a*100:.1f}% | {b*100:.1f}% |" for k, (a, b) in fr.items()]
    sm_ = metrics[metrics["model"].isin(["anch_blind", "anch_aware"])].copy()
    sm_["rs"] = sm_["seed_mae"].apply(lambda s: (max(s) - min(s)) / np.mean(s))
    L += ["", f"## 8. Seed stability: largest (max-min)/mean MAE across seeds **{sm_['rs'].max()*100:.2f}%** (median {sm_['rs'].median()*100:.2f}%)"]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout + r.stderr


@app.function(image=image, volumes=VOLUMES, timeout=120)
def versions() -> tuple[str, str]:
    data_vol.reload()
    return _latest("splits_sp-*.json", "split_version"), _latest("features_ft-*.json", "feature_version")


@app.local_entrypoint()
def reanalyze(exp_id: str):
    report = analyze.remote(exp_id)
    Path(f"docs/experiments/{exp_id}_phase5b_results.md").write_text(report, encoding="utf-8")
    print(report)


@app.local_entrypoint()
def main(git_sha: str = "unknown"):
    print(tests_remote.remote())
    sv, fv = versions.remote()
    chk = checks.remote(sv, fv)
    print("CHECKS:", json.dumps(chk))
    if not chk["split_identical"] or chk["daily_prefix_invariance"]["mismatching_origins"] != 0:
        raise SystemExit("STOP: split changed or daily features leak")
    res = run_phase5b.remote(git_sha, sv, fv)
    print("RUN:", json.dumps(res))
    if res["status"] == "written":
        print("REPRO:", json.dumps(repro_check.remote(sv, fv)))
    report = analyze.remote(res["experiment_id"])
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{res['experiment_id']}_phase5b_results.md").write_text(report, encoding="utf-8")
    print(report)
