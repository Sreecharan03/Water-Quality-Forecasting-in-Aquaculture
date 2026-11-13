"""Phase 5 jobs: baselines + LightGBM/XGBoost on the VALIDATION-side regimes only (fixed settings, no tuning).

Run from the repo root (profile selected via MODAL_PROFILE):
    modal run -m modal_jobs.phase5 --git-sha <sha>
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image

_CACHE: dict = {}


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _latest(glob: str, key: str) -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob(glob), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))[key]


def _data(split_version: str, feature_version: str):
    import pandas as pd
    k = (split_version, feature_version)
    if k not in _CACHE:
        data_vol.reload()
        feats = pd.concat([pd.read_parquet(f) for f in sorted(Path(DATA_MOUNT, "features", feature_version).glob("*.parquet"))],
                          ignore_index=True)
        a = pd.read_parquet(Path(DATA_MOUNT, "splits", split_version, "assignments.parquet"),
                            columns=["pond", "grid_idx", "window", "role", "fold", "block_day"])
        T = feats.merge(a, on=["pond", "grid_idx"], how="inner", validate="one_to_one")
        assert len(T) == len(feats) == len(a)
        man = json.loads(Path(DATA_MOUNT, "manifests", f"splits_{split_version}.json").read_text(encoding="utf-8"))
        _CACHE[k] = (T, man["info"], man["config"]["cv_folds"])
    return _CACHE[k]


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def run_task_remote(regime: str, var: str, h: int, split_version: str, feature_version: str) -> tuple[list, bytes]:
    from aquatic_xai.experiments.run import run_task
    from aquatic_xai.features.dictionary import feature_specs
    T, info, k = _data(split_version, feature_version)
    ecfg, mcfg = _yaml("models.yaml"), _yaml("models.yaml")["models"]
    specs = feature_specs(_yaml("features.yaml")["features"])
    metrics, preds = run_task(T, info, k, regime, var, h, specs, mcfg, ecfg["evaluation"]["low_quantile"])
    buf = io.BytesIO()
    preds.to_parquet(buf, index=False)
    return metrics, buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_phase5(git_sha: str, split_version: str = "", feature_version: str = "") -> dict:
    import hashlib
    import lightgbm, numpy, pandas, sklearn, xgboost
    cfg = _yaml("models.yaml")
    data_vol.reload()
    sv = split_version or _latest("splits_sp-*.json", "split_version")
    fv = feature_version or _latest("features_ft-*.json", "feature_version")
    exp_id = "exp-" + hashlib.sha256(json.dumps({"s": sv, "f": fv, "cfg": cfg, "code": "p5-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    if (out / "manifest.json").exists():
        return {"experiment_id": exp_id, "status": "already_exists"}
    ev = cfg["evaluation"]
    args = [(r, v, h, sv, fv) for r in cfg["regimes"] for v in ev["variables"] for h in ev["horizons"]]
    results = list(run_task_remote.starmap(args, order_outputs=True))
    (out / "preds").mkdir(parents=True, exist_ok=True)
    all_metrics = []
    for (r, v, h, _, _), (metrics, blob) in zip(args, results):
        (out / "preds" / f"{r}__{v}__h{h}.parquet").write_bytes(blob)
        all_metrics += metrics
    secs = sum(m.get("seconds", 0) for m in all_metrics if m["model"] == "_task")
    (out / "metrics.json").write_text(json.dumps(all_metrics, indent=1), encoding="utf-8")
    tmp = out / "manifest.json.part"
    tmp.write_text(json.dumps({
        "experiment_id": exp_id, "code_git_sha": git_sha, "split_version": sv, "feature_version": fv, "config": cfg,
        "versions": {"lightgbm": lightgbm.__version__, "xgboost": xgboost.__version__, "sklearn": sklearn.__version__,
                     "numpy": numpy.__version__, "pandas": pandas.__version__},
        "n_tasks": len(args), "task_seconds_total": round(secs, 1), "cpu_per_task": 2,
        "note": "validation-side regimes only; FINAL regimes not run"}, indent=2), encoding="utf-8")
    tmp.replace(out / "manifest.json")
    artifact_vol.commit()
    return {"experiment_id": exp_id, "status": "written", "n_tasks": len(args), "task_seconds_total": round(secs, 1),
            "split_version": sv, "feature_version": fv}


@app.function(image=image, volumes=VOLUMES, timeout=900)
def repro_check(split_version: str, feature_version: str) -> dict:
    """Run the same task in two separate containers and compare row-level errors."""
    import numpy as np
    import pandas as pd
    a = run_task_remote.remote("dev_future_seen_ponds", "DO", 4, split_version, feature_version)
    b = run_task_remote.remote("dev_future_seen_ponds", "DO", 4, split_version, feature_version)
    da, db = pd.read_parquet(io.BytesIO(a[1])), pd.read_parquet(io.BytesIO(b[1]))
    cols = [c for c in da.columns if c.startswith("ae_")]
    diff = {c: float(np.nanmax(np.abs(da[c].to_numpy() - db[c].to_numpy()))) for c in cols}
    return {"max_abs_diff_by_model": diff, "identical_rows": bool(da[["pond", "grid_idx"]].equals(db[["pond", "grid_idx"]]))}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def analyze(exp_id: str) -> str:
    import numpy as np
    import pandas as pd
    from aquatic_xai.experiments.evaluate import diff_ci, fmt, improvement_ci, mean_ci
    from aquatic_xai.experiments.run import MODEL_NAMES
    artifact_vol.reload()
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    metrics = pd.DataFrame(json.loads((out / "metrics.json").read_text(encoding="utf-8")))
    ev = man["config"]["evaluation"]
    B, seed0 = ev["bootstrap"]["B"], ev["bootstrap"]["seed"]
    grp = lambda r: "seen" if r == "dev_future_seen_ponds" else "unseen" if "future_unseen" in r else "diag"

    frames: dict = {}
    for f in sorted((out / "preds").glob("*.parquet")):
        r, v, h = f.stem.split("__")
        frames.setdefault((grp(r), v, int(h[1:])), []).append(pd.read_parquet(f))
    D = {k: pd.concat(v, ignore_index=True) for k, v in frames.items()}
    H, V = ev["horizons"], ev["variables"]
    hl = {1: "15 min", 4: "1 h", 24: "6 h"}
    cell = lambda g: [(g, h) for h in H]
    cols = [(g, h) for g in ("seen", "unseen") for h in H]
    head = "| model | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |\n|---|" + "---|" * len(cols)
    ctr = [0]

    def nxt():
        ctr[0] += 1
        return seed0 + ctr[0]

    L = [f"# Phase 5 leaderboard, experiment `{exp_id}`", "",
         f"- Split `{man['split_version']}`, features `{man['feature_version']}`, code commit `{man['code_git_sha'][:12]}`",
         f"- Versions: {man['versions']}",
         f"- Tasks: {man['n_tasks']} (9 regimes x 3 targets x 3 horizons); fixed settings, **no tuning**; seeds {man['config']['models']['seeds']}",
         f"- Compute: {man['task_seconds_total']} container-seconds on 2 CPU cores each (no GPU). Billing not read from the CLI.",
         "- **Validation-side only.** The sealed test windows and the 4 sealed ponds were not used.",
         "- 'seen' = dev ponds that were in training (future days). 'unseen' = pond groups held out of training (future days). "
         "Cells show average miss (MAE) in native units with a 95% blocked-bootstrap interval (blocks = pond x day).", ""]
    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    L.append("## 1. Average miss (MAE) by model")
    for v in V:
        L += ["", f"### {v} ({unit[v]})", "", head]
        for m in MODEL_NAMES:
            L.append(f"| {m} | " + " | ".join(fmt(mean_ci(D[(g, v, h)], f"ae_{m}", B, nxt())) for g, h in cols) + " |")
    L += ["", "## 2. Improvement over 'same as now' (positive = better than persistence; interval excluding 0 = clear)"]
    for v in V:
        L += ["", f"### {v}", "", head]
        for m in MODEL_NAMES[1:]:
            L.append(f"| {m} | " + " | ".join(fmt(improvement_ci(D[(g, v, h)], f"ae_{m}", "ae_persistence", B, nxt()), pct=True) for g, h in cols) + " |")

    L += ["", "## 3. Does data-quality information help? (aware minus blind, change in MAE; negative = aware better)", "",
          "| target | algorithm | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |", "|---|---|" + "---|" * len(cols)]
    for v in V:
        for algo in ("ridge", "lgbm", "xgb"):
            L.append(f"| {v} | {algo} | " + " | ".join(fmt(diff_ci(D[(g, v, h)], f"ae_{algo}_aware", f"ae_{algo}_blind", B, nxt()), digits=4) for g, h in cols) + " |")

    L += ["", "## 4. Pond-shift cost: same rows, model never saw the pond minus model that did (positive = worse on unseen ponds)", "",
          "| target | model | " + " | ".join(hl[h] for h in H) + " |", "|---|---|" + "---|" * len(H)]
    for v in V:
        for m in ("lgbm_blind", "lgbm_aware", "xgb_blind", "xgb_aware", "ridge_blind"):
            cells = []
            for h in H:
                s, u = D[("seen", v, h)], D[("unseen", v, h)]
                j = s[["pond", "grid_idx", "block_day", f"ae_{m}"]].merge(u[["pond", "grid_idx", f"ae_{m}"]], on=["pond", "grid_idx"], suffixes=("_seen", "_unseen"))
                cells.append(fmt(diff_ci(j, f"ae_{m}_unseen", f"ae_{m}_seen", B, nxt()), digits=3))
            L.append(f"| {v} | {m} | " + " | ".join(cells) + " |")

    L += ["", "## 5. Hard cases: bottom 10% of training values, unseen ponds (MAE with interval)", "",
          "| target | model | " + " | ".join(hl[h] for h in H) + " |", "|---|---|" + "---|" * len(H)]
    for v in V:
        for m in ("persistence", "seasonal_naive", "ridge_blind", "lgbm_blind", "lgbm_aware", "xgb_aware"):
            cells = []
            for h in H:
                d = D[("unseen", v, h)]
                d = d[d["y"] <= d["y_train_low"]]
                cells.append(f"{fmt(mean_ci(d, f'ae_{m}', B, nxt()))} (n={len(d)})")
            L.append(f"| {v} | {m} | " + " | ".join(cells) + " |")

    L += ["", "## 6. Optimism of the usual pond hold-out (same ponds as unseen, but on days the other ponds trained on)", "",
          "| target | model | " + " | ".join(f"{hl[h]} unseen-future / diagnostic" for h in H) + " |", "|---|---|" + "---|" * len(H)]
    for v in V:
        for m in ("persistence", "lgbm_aware"):
            L.append(f"| {v} | {m} | " + " | ".join(
                f"{mean_ci(D[('unseen', v, h)], f'ae_{m}', B, nxt())[0]:.3f} / {mean_ci(D[('diag', v, h)], f'ae_{m}', B, nxt())[0]:.3f}" for h in H) + " |")

    # seed spread
    sm = metrics[(metrics["regime"] == "dev_future_seen_ponds") & metrics["model"].isin(["lgbm_aware", "lgbm_blind", "xgb_aware", "xgb_blind"])].copy()
    sm["rel_spread"] = sm["seed_mae"].apply(lambda s: (max(s) - min(s)) / np.mean(s))
    L += ["", f"## 7. Seed stability: largest (max-min)/mean MAE across 3 seeds, seen regime: **{sm['rel_spread'].max()*100:.2f}%** "
              f"(median {sm['rel_spread'].median()*100:.2f}%)"]

    # MASE
    t = metrics[metrics["model"] == "_task"].copy()
    t["g"] = t["regime"].map(grp)
    sc = t.groupby(["g", "var", "h"]).apply(lambda x: np.average(x["mase_scale"], weights=x["n_eval"])).to_dict()
    L += ["", "## 8. MASE (MAE divided by the training-period persistence MAE; below 1 = better than persistence on average), unseen ponds", "",
          "| target | model | " + " | ".join(hl[h] for h in H) + " |", "|---|---|" + "---|" * len(H)]
    for v in V:
        for m in ("persistence", "seasonal_naive", "ridge_blind", "lgbm_blind", "lgbm_aware", "xgb_blind", "xgb_aware"):
            L.append(f"| {v} | {m} | " + " | ".join(f"{mean_ci(D[('unseen', v, h)], f'ae_{m}', B, nxt())[0] / sc[('unseen', v, h)]:.2f}" for h in H) + " |")

    # against the stronger baseline
    L += ["", "## 9. Against 'same time yesterday' (seasonal naive), same rows; positive = trained model better", "",
          "| target | model | " + " | ".join(f"{g} {hl[h]}" for g, h in cols) + " |", "|---|---|" + "---|" * len(cols)]
    for v in V:
        for m in ("ridge_blind", "lgbm_blind", "lgbm_aware", "xgb_blind", "xgb_aware"):
            L.append(f"| {v} | {m} | " + " | ".join(fmt(improvement_ci(D[(g, v, h)], f"ae_{m}", "ae_seasonal_naive", B, nxt()), pct=True) for g, h in cols) + " |")

    # plain verdicts
    wording = lambda ci: "clearly better than" if ci[1] > 0 else ("not clearly different from" if ci[2] > 0 else "clearly worse than")
    L += ["", "## 10. Plain verdicts (unseen ponds, future days; best trained model by improvement over 'same as now')", ""]
    for v in V:
        for h in H:
            d = D[("unseen", v, h)]
            best, bi = None, -9
            for m in MODEL_NAMES[2:]:
                imp = improvement_ci(d, f"ae_{m}", "ae_persistence", B, nxt())
                if imp[0] > bi:
                    best, bi, ci = m, imp[0], imp
            cs = improvement_ci(d, f"ae_{best}", "ae_seasonal_naive", B, nxt())
            L.append(f"- {v}, {hl[h]}: **{best}** is {wording(ci)} 'same as now' ({ci[0]*100:+.1f}%, interval {ci[1]*100:+.1f} to {ci[2]*100:+.1f}) "
                     f"and {wording(cs)} 'same time yesterday' ({cs[0]*100:+.1f}%, interval {cs[1]*100:+.1f} to {cs[2]*100:+.1f}).")
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout + r.stderr


@app.local_entrypoint()
def reanalyze(exp_id: str):
    report = analyze.remote(exp_id)
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{exp_id}_leaderboard.md").write_text(report, encoding="utf-8")   # aggregates only
    print("report written:", len(report), "chars")


@app.local_entrypoint()
def main(git_sha: str = "unknown"):
    print(tests_remote.remote())
    res = run_phase5.remote(git_sha)
    print("RUN:", json.dumps(res))
    rc = repro_check.remote(res.get("split_version", ""), res.get("feature_version", "")) if res["status"] == "written" else None
    print("REPRO CHECK (same task in two containers):", json.dumps(rc))
    report = analyze.remote(res["experiment_id"])
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{res['experiment_id']}_leaderboard.md").write_text(report, encoding="utf-8")   # aggregates only
    print(report)
