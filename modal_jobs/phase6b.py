"""Phase 6b: calibrate alert probabilities and choose the alert level on other pond groups. No new model fitting.
Rules: configs/phase6b.yaml (written before running).

    modal run -m modal_jobs.phase6b::main --git-sha <sha>
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _latest(glob: str, key: str) -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob(glob), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))[key]


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def run_phase6b(git_sha: str) -> str:
    import hashlib
    import numpy as np
    import pandas as pd
    from aquatic_xai.alerts.calibrate import brier, choose_level, evaluate_level, false_alarm_flags, fit_isotonic
    from aquatic_xai.alerts.evaluate import match_recall_threshold
    from aquatic_xai.alerts.labels import episode_onsets
    from aquatic_xai.experiments.evaluate import mean_ci
    data_vol.reload()
    artifact_vol.reload()
    cfg = {"phase6b": _yaml("phase6b.yaml"), "phase6": _yaml("phase6.yaml")}
    cc, dr = cfg["phase6b"]["alerts_calibration"], cfg["phase6b"]["decision_rule"]
    exp_id = "exp-" + hashlib.sha256(json.dumps({"cfg": cfg, "code": "p6b-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    src = Path(ARTIFACT_MOUNT, "experiments", cc["source_experiment"])
    srcman = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    thr_mg = srcman["config"]["alerts"]["threshold_mg_l"]
    fv = srcman["feature_version"]
    T = pd.concat([pd.read_parquet(f, columns=["pond", "grid_idx", "DO_cur"]) for f in sorted(Path(DATA_MOUNT, "features", fv).glob("*.parquet"))], ignore_index=True)
    lead_min, lead_max = dr["episode"]["lead_min_slots"], dr["episode"]["lead_max_slots"]
    onsets = {p: episode_onsets(g, thr_mg, dr["episode"]["quiet_slots"]) for p, g in T.groupby("pond", sort=False)}
    B, seed0, lv = dr["bootstrap"]["B"], dr["bootstrap"]["seed"], dr["bootstrap"]["level"]
    Wn = {v: k for k, v in cc["windows"].items()}

    def fold_rows(W):
        return {k: pd.read_parquet(src / "alerts" / f"dev_future_unseen_fold{k}__W{W}.parquet") for k in range(4)}

    L = [f"# Phase 6b results, experiment `{exp_id}`", "",
         f"- Reuses the Phase 6 alert predictions (`{cc['source_experiment']}`); no model was refitted. Split `{srcman['split_version']}` unchanged. Validation-side only; sealed test not used.",
         f"- Code commit `{git_sha[:12]}`. Contract: `configs/phase6b.yaml`, written before running. One round.", ""]

    # ---- A. calibration
    L += ["## A. Are the probabilities now trustworthy? (unseen ponds; isotonic fitted on the other three pond groups)", "",
          "| window | Brier raw | Brier calibrated | bins (calibrated prediction -> actual rate, n) | criterion |", "|---|---|---|---|---|"]
    calib_ok = []
    calibrators = {}
    cal_rows_by_W, fold_parts = {}, {}
    for W in cc["windows"].values():
        F = fold_rows(W)
        parts = []
        for k in range(4):
            others = pd.concat([F[j] for j in range(4) if j != k])
            iso = fit_isotonic(others["p_model"].to_numpy(), others["y"].to_numpy())
            d = F[k].copy()
            d["p_cal"] = iso.predict(d["p_model"].to_numpy())
            parts.append(d)
        D = pd.concat(parts, ignore_index=True)
        cal_rows_by_W[W] = D
        fold_parts[W] = parts
        allr = pd.concat(F.values())
        iso_all = fit_isotonic(allr["p_model"].to_numpy(), allr["y"].to_numpy())
        calibrators[Wn[W]] = {"x": [float(x) for x in iso_all.X_thresholds_], "y": [float(x) for x in iso_all.y_thresholds_]}
        braw, bcal = brier(D["p_model"], D["y"]), brier(D["p_cal"], D["y"])
        bins = pd.cut(D["p_cal"], [0, .1, .3, .5, .7, .9, 1.0001], include_lowest=True)
        g = D.groupby(bins, observed=False).agg(n=("y", "size"), rate=("y", "mean"), pm=("p_cal", "mean"))
        big = g[g["n"] >= 100]
        ok = bcal < braw and bool(((big["pm"] - big["rate"]).abs() <= 0.10).all())
        calib_ok.append(ok)
        L.append(f"| {Wn[W]} | {braw:.4f} | {bcal:.4f} | " + "; ".join(f"{x.pm*100:.0f}% -> {x.rate*100:.0f}% ({int(x.n)})" for x in g.itertuples() if x.n) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{sum(calib_ok)} of 3 windows pass** ({cc['calibration_success']}). Calibration changes the displayed probability only; it does not change the ranking of risk (average precision is unchanged up to ties)."]

    # ---- B. decision rule, 6 h
    W = dr["window"]
    F = fold_rows(W)
    folds = []
    pooled = {"model": {"episodes": 0, "caught": 0, "leads": []}, "yday": {"episodes": 0, "caught": 0, "leads": []}}
    fa_parts = []
    L += ["", "## B. Alert level chosen on other pond groups (6 h window), then applied to the held-out pond group", "",
          f"Rule: the strictest alert level that catches at least {int(dr['target_episode_recall']*100)}% of episodes on the other three pond groups. The baseline 'same window yesterday' gets its level chosen the same way.", "",
          "| held-out group | model level (raw / calibrated) | model recall | model false-alarm days | baseline level | baseline recall | baseline false-alarm days |", "|---|---|---|---|---|---|---|"]
    for k in range(4):
        cal = pd.concat([F[j] for j in range(4) if j != k])
        ev = fold_parts[W][k]            # held-out fold k rows, with isotonic fitted on the other folds
        tm, _ = choose_level(cal, onsets, "p_model", dr["target_episode_recall"], lead_min, lead_max)
        tb, _ = choose_level(cal, onsets, "s_yday", dr["target_episode_recall"], lead_min, lead_max)
        iso = fit_isotonic(cal["p_model"].to_numpy(), cal["y"].to_numpy())
        sm = evaluate_level(ev, onsets, "p_model", tm, lead_min, lead_max)
        sb = evaluate_level(ev, onsets, "s_yday", tb, lead_min, lead_max)
        fm, fb = false_alarm_flags(ev, "p_model", tm), false_alarm_flags(ev, "s_yday", tb)
        fa_parts.append(fm.merge(fb, on=["pond", "block_day"], suffixes=("_m", "_b")))
        for key, st in (("model", sm), ("yday", sb)):
            pooled[key]["episodes"] += st["episodes"]
            pooled[key]["caught"] += st["caught"]
            pooled[key]["leads"] += st["leads"]
        folds.append((k, tm, float(iso.predict([tm])[0]), sm, tb, sb))
        L.append(f"| fold {k} | {tm:.3f} / {float(iso.predict([tm])[0])*100:.0f}% | {sm['caught']}/{sm['episodes']} ({sm['recall']*100:.0f}%) | {sm['false_alarm_pond_days']}/{sm['pond_days']} | {tb:.3f} | {sb['caught']}/{sb['episodes']} ({sb['recall']*100:.0f}%) | {sb['false_alarm_pond_days']}/{sb['pond_days']} |")
    FA = pd.concat(fa_parts, ignore_index=True)
    FA["diff"] = FA["fa_m"] - FA["fa_b"]
    dci = mean_ci(FA, "diff", B, seed0, lv)
    rm = pooled["model"]["caught"] / pooled["model"]["episodes"]
    rb = pooled["yday"]["caught"] / pooled["yday"]["episodes"]
    ok = dci[2] < 0 and rm >= rb - 0.05
    L += ["", "### Pooled over the 4 held-out pond groups (the pre-registered test)", "",
          "| method | episodes | caught | recall | median warning (h) | share of pond-days with a false alarm |", "|---|---|---|---|---|---|",
          f"| model | {pooled['model']['episodes']} | {pooled['model']['caught']} | {rm*100:.0f}% | {np.median(pooled['model']['leads']):.2f} | {FA['fa_m'].mean()*100:.0f}% |",
          f"| same window yesterday | {pooled['yday']['episodes']} | {pooled['yday']['caught']} | {rb*100:.0f}% | {np.median(pooled['yday']['leads']):.2f} | {FA['fa_b'].mean()*100:.0f}% |", "",
          f"Difference in false-alarm share (model minus baseline): **{dci[0]*100:+.1f} points** (99% interval {dci[1]*100:+.1f} to {dci[2]*100:+.1f}; blocks = pond-days, n={len(FA)}). "
          f"Recall difference (model minus baseline): {(rm-rb)*100:+.0f} points.", "",
          f"**Pre-registered verdict: {'PASS' if ok else 'FAIL'}** ({dr['success']})."]

    # secondary: baseline matched on held-out data
    allw = pd.concat(F.values(), ignore_index=True)
    tm_all, sm_all = choose_level(allw, onsets, "p_model", dr["target_episode_recall"], lead_min, lead_max)
    tb_m, sb_m = match_recall_threshold(allw, onsets, "s_yday", rm, lead_min, lead_max)
    L += ["", "### Secondary (favours the baseline): baseline given the strictest level that matches the model's realised recall on the same held-out data", "",
          f"- Baseline recall {sb_m['recall']*100:.0f}%, false-alarm pond-days {sb_m['false_alarm_pond_days']}/{sb_m['pond_days']} ({sb_m['false_alarm_day_share']*100:.0f}%), median warning {sb_m['median_lead_h']:.2f} h."]

    # app-ready operating point from all four groups
    iso_all6 = fit_isotonic(allw["p_model"].to_numpy(), allw["y"].to_numpy())
    app_cal = float(iso_all6.predict([tm_all])[0])
    L += ["", "## C. Operating point for the app (chosen on all four pond groups, so it is NOT an independent test)", "",
          f"- Alert when the model's raw probability is at least **{tm_all:.3f}**, which is a calibrated probability of about **{app_cal*100:.0f}%**. "
          f"On these groups it catches {sm_all['caught']}/{sm_all['episodes']} episodes ({sm_all['recall']*100:.0f}%), with a false alarm on {sm_all['false_alarm_day_share']*100:.0f}% of pond-days.",
          "- Calibrator lookup tables are stored in `calibrators.json` in the experiment folder (for the app and Phase 9)."]
    md = "\n".join(L)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(md, encoding="utf-8")
    (out / "calibrators.json").write_text(json.dumps({"calibrators": calibrators, "alert_level_raw_6h": tm_all, "alert_level_calibrated_6h": app_cal}, indent=1), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"experiment_id": exp_id, "code_git_sha": git_sha, "config": cfg, "source": cc["source_experiment"]}, indent=2), encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout[-300:] + r.stderr[-300:]


@app.local_entrypoint()
def main(git_sha: str = "unknown"):
    print(tests_remote.remote())
    report = run_phase6b.remote(git_sha)
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    eid = report.split("`")[1]
    Path(f"docs/experiments/{eid}_phase6b_results.md").write_text(report, encoding="utf-8")
    print(report)
