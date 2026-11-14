"""Phases 7 and 8: SHAP explanations and explanation validation. Contract: configs/explain.yaml (written before any SHAP value existed).

    modal run -m modal_jobs.phase7::main --git-sha <sha>
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, VOLUMES, app, artifact_vol, image
from modal_jobs.loaders import feature_cfg, load, versions as ds_versions, yaml_cfg

ANCHORS = {"eluru": {1: "persistence", 4: "persistence", 24: "yesterday"}, "salt_marsh": {1: "persistence", 2: "persistence", 12: "yesterday"}}
DSKEY = {"eluru": "eluru", "salt_marsh": "salt_marsh"}


def _tasks(cfg: dict) -> list[tuple]:
    regs = [cfg["regimes"]["main"]] + cfg["regimes"]["pond_stability"]
    out = []
    for ds, spec in cfg["cells"].items():
        for var, hs in spec["forecasts"].items():
            for h in hs:
                out += [(ds, "F", f"{var}|{h}", r) for r in regs]
        for W in spec["alerts_windows_steps"]:
            out += [(ds, "A", f"DO|{W}", r) for r in regs]
    return out


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def explain_remote(ds: str, kind: str, key: str, regime: str, sv: str, fv: str):
    from aquatic_xai.explain.run import explain_alert_task, explain_forecast_task
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    cfg = yaml_cfg("explain.yaml")
    T, info, k = load(ds, sv, fv, alerts=(kind == "A"))
    fc = feature_cfg(ds)
    params = yaml_cfg("models.yaml")["models"]["lightgbm"]
    var, n = key.split("|")
    n = int(n)
    if kind == "F":
        res, frame = explain_forecast_task(T, info, k, regime, var, n, feature_specs(fc), daily_specs(fc["horizons"]), params, ANCHORS[ds], cfg["seeds"])
    else:
        res, frame = explain_alert_task(T, info, k, regime, n, feature_specs(fc), daily_specs(fc["horizons"]), params, cfg["seeds"])
    buf = io.BytesIO()
    frame.to_parquet(buf, index=False)
    return json.dumps(res), buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_phase7(git_sha: str, vers: dict) -> dict:
    cfg = yaml_cfg("explain.yaml")
    exp_id = "exp-" + hashlib.sha256(json.dumps({"v": vers, "cfg": cfg, "models": yaml_cfg("models.yaml")["models"], "code": "p7-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    if (out / "manifest.json").exists():
        return {"experiment_id": exp_id, "status": "already_exists"}
    tasks = _tasks(cfg)
    args = [(ds, kind, key, regime, vers[ds][0], vers[ds][1]) for ds, kind, key, regime in tasks]
    results = list(explain_remote.starmap(args, order_outputs=True))
    (out / "tasks").mkdir(parents=True, exist_ok=True)
    for (ds, kind, key, regime), (js, blob) in zip(tasks, results):
        stem = f"{ds}__{kind}__{key.replace('|', '_')}__{regime}"
        (out / "tasks" / f"{stem}.json").write_text(js, encoding="utf-8")
        (out / "tasks" / f"{stem}.parquet").write_bytes(blob)
    (out / "manifest.json").write_text(json.dumps({"experiment_id": exp_id, "code_git_sha": git_sha, "versions": vers, "config": cfg, "n_tasks": len(tasks),
                                                   "note": "validation-side only; sealed data not used"}, indent=2), encoding="utf-8")
    artifact_vol.commit()
    return {"experiment_id": exp_id, "status": "written", "n_tasks": len(tasks)}


@app.function(image=image, volumes=VOLUMES, timeout=900)
def repro_check(vers: dict) -> dict:
    import numpy as np
    a = json.loads(explain_remote.remote("eluru", "F", "Temp|24", "dev_future_unseen_fold1", *vers["eluru"])[0])
    b = json.loads(explain_remote.remote("eluru", "F", "Temp|24", "dev_future_unseen_fold1", *vers["eluru"])[0])
    d = max(float(np.max(np.abs(np.array(a["mean_abs"][s]) - np.array(b["mean_abs"][s])))) for s in a["mean_abs"])
    return {"max_abs_diff_mean_abs_shap": d, "same_top5": a["top5_train_subsample"] == b["top5_train_subsample"]}


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def analyze7(exp_id: str) -> str:
    import itertools
    import numpy as np
    import pandas as pd
    from aquatic_xai.experiments.evaluate import mean_ci
    from aquatic_xai.explain.shap_utils import family_map, family_of, family_shares, safe_spearman, top_k
    from aquatic_xai.features.daily import daily_columns
    from aquatic_xai.features.dictionary import feature_specs
    artifact_vol.reload()
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    cfg = man["config"]
    t4 = cfg["phase8_tests"]
    B, seed0, lv = t4["bootstrap"]["B"], t4["bootstrap"]["seed"], t4["bootstrap"]["level"]
    main_r, folds = cfg["regimes"]["main"], cfg["regimes"]["pond_stability"]
    R = {}
    for f in sorted((out / "tasks").glob("*.json")):
        ds, kind, key, regime = f.stem.split("__")
        R[(ds, kind, key, regime)] = (json.loads(f.read_text(encoding="utf-8")), pd.read_parquet(f.with_suffix(".parquet")))
    cells = sorted({(ds, kind, key) for ds, kind, key, _ in R})
    hl = {("eluru", 1): "15 min", ("eluru", 4): "1 h", ("eluru", 24): "6 h", ("salt_marsh", 1): "30 min", ("salt_marsh", 2): "1 h", ("salt_marsh", 12): "6 h"}
    awl = {4: "1 h", 12: "3 h", 24: "6 h"}
    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    dsname = {"eluru": "Eluru farm ponds", "salt_marsh": "salt-marsh ponds"}

    def label(ds, kind, key):
        var, n = key.split("_") if "_" in key else key.split("|")
        n = int(n)
        return f"{dsname[ds]}: {var} {hl[(ds, n)]} ahead" if kind == "F" else f"{dsname[ds]}: low-oxygen alert, next {awl[n]}"

    def fmap(ds):
        fc = feature_cfg(ds)
        return family_map(feature_specs(fc), daily_columns(fc["horizons"]))

    def split_key(key):
        var, n = key.split("_")
        return var, int(n)

    rows, details, fam_rows, ctr = [], [], [], [0]
    expect = {"X1": [], "X2": [], "X3": []}
    shortest = {}
    for ds, kind, key in cells:
        if kind == "F":
            var, n = split_key(key)
            shortest[(ds, var)] = min(shortest.get((ds, var), 10**9), n)
    for ds, kind, key in cells:
        res_main, fr_main = R[(ds, kind, key, main_r)]
        names, fm = res_main["names"], fmap(ds)
        seeds = sorted(res_main["mean_abs"])
        vecs = {s: np.array(res_main["mean_abs"][s]) for s in seeds}
        e1 = min(safe_spearman(vecs[a], vecs[b]) for a, b in itertools.combinations(seeds, 2))
        fv = [np.array(R[(ds, kind, key, r)][0]["mean_abs"][seeds[0]]) for r in folds]
        pairs = list(itertools.combinations(range(len(folds)), 2))
        e2a = float(np.nanmean([safe_spearman(fv[i], fv[j]) for i, j in pairs]))
        e2b = float(np.mean([len(set(top_k(fv[i], 5)) & set(top_k(fv[j], 5))) for i, j in pairs]))
        e3 = safe_spearman(np.array(res_main["half_first"]), np.array(res_main["half_second"]))
        e4 = {}
        for r in [main_r] + folds:
            fr = R[(ds, kind, key, r)][1].copy()
            fr["diff"] = fr["loss_top"] - fr["loss_rand"]
            ctr[0] += 1
            e4[r] = mean_ci(fr, "diff", B, seed0 + ctr[0], lv)
        e4_main = e4[main_r][1] > 0
        e4_folds = sum(e4[r][1] > 0 for r in folds)
        p1, p2, p3, p4 = e1 >= 0.90, (e2a >= 0.70 and e2b >= 3), e3 >= 0.70, (e4_main and e4_folds >= 3)
        rows.append((label(ds, kind, key), e1, p1, e2a, e2b, p2, e3, p3, e4[main_r], e4_folds, p4, all((p1, p2, p3, p4))))
        avg = np.mean([vecs[s] for s in seeds], axis=0)
        order = top_k(avg, 10)
        u = unit.get(split_key(key)[0], "") if kind == "F" else "log-odds"
        details.append((label(ds, kind, key), u, [(names[i], family_of(names[i], fm), float(avg[i])) for i in order], res_main, kind))
        sh = family_shares(avg, names, fm)
        fam_rows.append((label(ds, kind, key), sh))
        if kind == "F":
            var, n = split_key(key)
            if var in ("DO", "Temp") and n == max(cfg["cells"][ds]["forecasts"][var]) and n in (24, 12):
                expect["X1"].append((label(ds, kind, key), sh.get("daily", 0.0), sh.get("daily", 0.0) >= 0.25))
            if n == shortest[(ds, var)]:
                expect["X2"].append((label(ds, kind, key), sh.get("history", 0.0), sh.get("history", 0.0) >= 0.50))
            if var == "Temp":
                top3 = [f for f, _ in sorted(sh.items(), key=lambda kv: -kv[1])[:3]]
                expect["X3"].append((label(ds, kind, key), ", ".join(top3), "time" in top3))

    L = [f"# Phases 7 and 8 results: SHAP explanations and explanation validation, experiment `{exp_id}`", "",
         f"- Contract `configs/explain.yaml` (written before any SHAP value existed). Code commit `{man['code_git_sha'][:12]}`. Validation-side only; sealed ponds and test windows not used.",
         "- The explained models are the same anchored LightGBM models (quality-blind, fixed settings, seeds 0 to 2) evaluated in earlier phases. TreeSHAP is exact for tree models.",
         "- **How to read this:** SHAP says how much each input pushed a prediction up or down compared with the model's average output. For forecasts, SHAP explains the model's **correction** to its starting guess (same as now, or same time yesterday). It describes what the **model** uses, not proof of what causes oxygen to fall.", "",
         "## Phase 8: are the explanations trustworthy? (pre-registered tests E1 to E4)", "",
         "| cell | E1 same across seeds (min rank correlation, need 0.90) | E2 same across pond groups (mean rank corr need 0.70; shared top-5 need 3) | E3 same across time (need 0.70) | E4 removing top-5 hurts more than removing 5 random (main; ponds passing of 4, need main and 3) | validated |",
         "|---|---|---|---|---|---|"]
    for lab_, e1, p1, e2a, e2b, p2, e3, p3, e4m, e4f, p4, ok in rows:
        L.append(f"| {lab_} | {e1:.2f} {'PASS' if p1 else 'fail'} | {e2a:.2f} / {e2b:.1f} {'PASS' if p2 else 'fail'} | {e3:.2f} {'PASS' if p3 else 'fail'} | "
                 f"extra error {e4m[0]:+.3f} [{e4m[1]:+.3f}, {e4m[2]:+.3f}]; {e4f}/4 {'PASS' if p4 else 'fail'} | **{'YES' if ok else 'NO'}** |")
    nval = sum(1 for r in rows if r[-1])
    L += ["", f"**{nval} of {len(rows)} explanations are validated** (all of E1 to E4 must pass). E4 extra error is in the loss unit of the cell (forecast absolute error, or alert log-loss), 99% interval."]

    L += ["", "## Phase 7: what do the models use? (mean absolute SHAP, validation window, averaged over 3 seeds)"]
    for lab_, u, top, res_main, kind in details:
        L += ["", f"### {lab_} (unit: {u})", "", "| rank | input | family | mean abs SHAP |", "|---|---|---|---|"]
        for i, (n_, f_, v_) in enumerate(top, 1):
            L.append(f"| {i} | `{n_}` | {f_} | {v_:.4f} |")
    L += ["", "### Share of total attribution by input family (main regime)", "", "| cell | history | rolling | daily-pattern | time of day | anchor gap |", "|---|---|---|---|---|---|"]
    for lab_, sh in fam_rows:
        def g(k):
            return f"{sh.get(k, 0.0)*100:.0f}%" if k in sh else "-"
        L.append(f"| {lab_} | {g('history')} | {g('rolling')} | {g('daily')} | {g('time')} | {g('anchor_gap')} |")

    L += ["", "## Pre-registered expectations (descriptive, not gating)", ""]
    desc = {"X1": "At 6 h, the daily-pattern family carries at least 25% of attribution (oxygen, temperature)",
            "X2": "At the shortest explained horizon, the history family carries at least 50%", "X3": "For temperature, time of day is among the top 3 families"}
    for k in ("X1", "X2", "X3"):
        L += [f"**{k}: {desc[k]}**", "", "| cell | value | met |", "|---|---|---|"]
        for lab_, v_, met in expect[k]:
            L.append(f"| {lab_} | {v_ if isinstance(v_, str) else format(v_ * 100, '.0f') + '%'} | {'met' if met else 'not met'} |")
        L.append("")

    L += ["## Example explanations (anonymised, a few rows; signed SHAP)", ""]
    for lab_, u, top, res_main, kind in details:
        if res_main.get("examples"):
            L.append(f"**{lab_}**")
            for ex in res_main["examples"]:
                head = f"p(event)={ex['p_event']:.2f}" if kind == "A" else f"model correction {ex['pred_correction']:+.3f} on top of the anchor {ex['anchor']:.2f}"
                L.append(f"- {head}: " + "; ".join(f"`{t['feature']}`={t['value'] if t['value'] is None else round(t['value'], 2)} ({t.get('shap_log_odds', t.get('shap')):+.3f})" for t in ex["top"]))
            L.append("")
    L += ["## Limits", "- Explanations describe the model, not causes in the pond.",
          "- Correlated inputs share attribution, so single-feature rankings are less stable than family shares.",
          "- Faithfulness is tested by replacing inputs with training medians, which can create unusual input combinations.",
          "- Only cells where a model helped were explained; the 4 held-out pond groups are 1 to 4 ponds each, so stability across groups is coarse."]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout[-300:] + r.stderr[-300:]


@app.function(image=image, volumes=VOLUMES, timeout=300)
def all_versions() -> dict:
    return {"eluru": list(ds_versions("eluru")), "salt_marsh": list(ds_versions("salt_marsh"))}


@app.local_entrypoint()
def main(git_sha: str = "unknown"):
    print(tests_remote.remote())
    vers = all_versions.remote()
    res = run_phase7.remote(git_sha, vers)
    print("RUN:", json.dumps(res))
    if res["status"] == "written":
        print("REPRO:", json.dumps(repro_check.remote(vers)))
    report = analyze7.remote(res["experiment_id"])
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{res['experiment_id']}_explanations.md").write_text(report, encoding="utf-8")
    print(report)


@app.local_entrypoint()
def reanalyze(exp_id: str):
    report = analyze7.remote(exp_id)
    Path(f"docs/experiments/{exp_id}_explanations.md").write_text(report, encoding="utf-8")
    print(report)
