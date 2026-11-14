"""Phase 6: forecast ranges (conformal) and low-oxygen early warning. Validation-side only. Rules: configs/phase6.yaml.

    modal run -m modal_jobs.phase6::main --git-sha <sha>
    modal run -m modal_jobs.phase6::show_prevalence      # descriptive counts only (already run)
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


def _alert_data(sv: str, fv: str):
    from aquatic_xai.alerts.labels import add_alert_columns
    k = ("alerts", sv, fv)
    if k not in _CACHE:
        T, info, kf, a, man = _data(sv, fv)
        ac = _yaml("phase6.yaml")["alerts"]
        _CACHE[k] = (add_alert_columns(T, ac["windows"], ac["threshold_mg_l"]), info, kf, a, man)
    return _CACHE[k]


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def prevalence() -> str:
    """How often is DO low? Descriptive counts on dev_train / dev_val only (no model)."""
    import numpy as np
    import pandas as pd
    from aquatic_xai.alerts.labels import episode_onsets, window_labels
    sv, fv = _latest("splits_sp-*.json", "split_version"), _latest("features_ft-*.json", "feature_version")
    full = _data(sv, fv)[0]
    T = full[~full["is_warmup"] & full["DO_cur"].notna()]
    L = []
    for role in ("dev_train", "dev_val"):
        d = T[T["role"] == role]
        L.append(f"## role={role}: {len(d)} readings, {d['pond'].nunique()} ponds")
        for thr in (2.0, 3.0, 4.0):
            L.append(f"- DO < {thr}: {(d['DO_cur'] < thr).mean()*100:.2f}% of readings; ponds with any: {int((d.groupby('pond')['DO_cur'].min() < thr).sum())}")
    for thr in (2.0, 3.0, 4.0):
        row = [f"thr={thr}"]
        for W in (4, 12, 24):
            labs, ons = [], 0
            for pond, g in full.groupby("pond", sort=False):
                lab, _ = window_labels(g, W, thr)
                msk = (~g["is_warmup"].to_numpy()) & ~np.isnan(lab) & g["role"].isin(["dev_train", "dev_val"]).to_numpy()
                labs.append(pd.DataFrame({"role": g["role"].to_numpy()[msk], "lab": lab[msk]}))
                if W == 24:
                    ons += int(g.set_index("grid_idx")["role"].reindex(episode_onsets(g, thr)).isin(["dev_train", "dev_val"]).sum())
            lb = pd.concat(labs)
            tr, va = lb[lb["role"] == "dev_train"]["lab"], lb[lb["role"] == "dev_val"]["lab"]
            row.append(f"W={W}: train {tr.mean()*100:.1f}%, val {va.mean()*100:.1f}%")
        row.append(f"episodes={ons}")
        L.append(" | ".join(row))
    return "\n".join(L)


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def checks(sv: str, fv: str) -> dict:
    """Split frozen? Labels re-derived independently? Yesterday-window feature leak-free on real tables?"""
    import numpy as np
    from aquatic_xai.alerts.labels import window_labels
    from aquatic_xai.splits.manifest import content_hash
    T, _, _, a, man = _alert_data(sv, fv)
    ac = _yaml("phase6.yaml")["alerts"]
    thr = ac["threshold_mg_l"]
    res = {"split_identical": content_hash(a) == man["assignments_content_hash"]}
    rng = np.random.RandomState(20261020)
    n_lab = bad_lab = n_pre = bad_pre = 0
    for pond, g in T.groupby("pond", sort=False):
        g = g.reset_index(drop=True)
        gi = g["grid_idx"].to_numpy()
        do = dict(zip(gi, g["DO_cur"].to_numpy(dtype=float)))
        ok = np.where(~g["is_warmup"].to_numpy() & (gi < gi.max() - 30) & (gi > 130))[0]
        for r in np.sort(rng.choice(ok, size=min(30, len(ok)), replace=False)):
            for name, W in ac["windows"].items():
                vals = [do.get(int(gi[r]) + k, np.nan) for k in range(1, W + 1)]
                v = np.array(vals, dtype=float)
                exp = 1.0 if np.nanmin(np.append(v, np.inf)) < thr else (0.0 if np.isfinite(v).sum() >= np.ceil(W / 2) else np.nan)
                got = g.loc[r, f"lab_W{W}"]
                n_lab += 1
                bad_lab += not ((np.isnan(exp) and np.isnan(got)) or exp == got)
                # prefix invariance of the yesterday-window feature
                pre = g.iloc[: r + 1][["grid_idx", "DO_cur"]]
                _, yd = window_labels(pre, W, thr)
                a_, b_ = yd[-1], g.loc[r, f"ydaymin_W{W}"]
                n_pre += 1
                bad_pre += not ((np.isnan(a_) and np.isnan(b_)) or a_ == b_)
    res["label_rederivation"] = {"checked": n_lab, "mismatches": bad_lab}
    res["ydaymin_prefix_invariance"] = {"checked": n_pre, "mismatches": bad_pre}
    return res


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0, max_containers=10)
def alert_task_remote(regime: str, W: int, sv: str, fv: str) -> bytes:
    from aquatic_xai.alerts.run import run_alert_task
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    T, info, kf, _, _ = _alert_data(sv, fv)
    f = _yaml("features.yaml")["features"]
    ac = _yaml("phase6.yaml")["alerts"]
    out = run_alert_task(T, info, kf, regime, W, feature_specs(f), daily_specs(f["horizons"]), _yaml("models.yaml")["models"]["lightgbm"], ac["seeds"])
    buf = io.BytesIO()
    out.to_parquet(buf, index=False)
    return buf.getvalue()


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_phase6(git_sha: str, sv: str, fv: str) -> dict:
    import hashlib
    cfg = _yaml("phase6.yaml")
    exp_id = "exp-" + hashlib.sha256(json.dumps({"s": sv, "f": fv, "cfg": cfg, "code": "p6-v1"}, sort_keys=True).encode()).hexdigest()[:12]
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    if (out / "manifest.json").exists():
        return {"experiment_id": exp_id, "status": "already_exists"}
    ac = cfg["alerts"]
    args = [(r, W, sv, fv) for r in ac["regimes"] for W in ac["windows"].values()]
    blobs = list(alert_task_remote.starmap(args, order_outputs=True))
    (out / "alerts").mkdir(parents=True, exist_ok=True)
    for (r, W, _, _), blob in zip(args, blobs):
        (out / "alerts" / f"{r}__W{W}.parquet").write_bytes(blob)
    tmp = out / "manifest.json.part"
    tmp.write_text(json.dumps({"experiment_id": exp_id, "code_git_sha": git_sha, "split_version": sv, "feature_version": fv,
                               "config": cfg, "n_alert_tasks": len(args), "note": "validation-side only; FINAL regimes not run"}, indent=2), encoding="utf-8")
    tmp.replace(out / "manifest.json")
    artifact_vol.commit()
    return {"experiment_id": exp_id, "status": "written", "n_alert_tasks": len(args)}


@app.function(image=image, volumes=VOLUMES, timeout=900)
def repro_check(sv: str, fv: str) -> dict:
    import numpy as np
    import pandas as pd
    a = pd.read_parquet(io.BytesIO(alert_task_remote.remote("dev_future_unseen_fold1", 24, sv, fv)))
    b = pd.read_parquet(io.BytesIO(alert_task_remote.remote("dev_future_unseen_fold1", 24, sv, fv)))
    return {"max_abs_diff_p": float(np.max(np.abs(a["p_model"].to_numpy() - b["p_model"].to_numpy()))), "rows": int(len(a)),
            "identical_rows": bool(a[["pond", "grid_idx"]].equals(b[["pond", "grid_idx"]]))}


def _conformal_report(cfg: dict, hl: dict) -> list[str]:
    import numpy as np
    import pandas as pd
    from aquatic_xai.experiments.evaluate import mean_ci
    from aquatic_xai.uncertainty.conformal import conformal_q
    cc = cfg["conformal"]
    B, seed0, lv = cc["bootstrap"]["B"], cc["bootstrap"]["seed"], cc["bootstrap"]["level"]
    d0, d1 = cc["day_hours"]
    src = Path(ARTIFACT_MOUNT, "experiments", cc["source_experiment"], "preds")
    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    L = ["## A. Forecast ranges (split-conformal), unseen ponds", "",
         f"Target: the range contains the truth {int((1-cc['alpha'])*100)}% of the time. Calibration = errors on the other three pond groups (disjoint ponds). "
         "Centre of each range = the Phase 5b recommended predictor for that cell. Coverage intervals are 95% blocked-bootstrap.", "",
         "| target | ahead | centre | coverage (plain) | width plain | width if centred on 'same as now' | day / night / low-value coverage | coverage (day/night variant) | day / night / low | per-fold coverage (min-max) | verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    ctr = [0]
    decisions = []
    for v in ("DO", "pH", "Temp"):
        for h in (1, 4, 24):
            pick = {str(k): x for k, x in cc["chosen_predictor"][v].items()}[str(h)]     # JSON manifest turns int keys into strings
            col = f"ae_{pick}"
            F = {k: pd.read_parquet(src / f"dev_future_unseen_fold{k}__{v}__h{h}.parquet") for k in range(4)}
            rows, per_fold = [], []
            wide, wide_p = [], []
            for k in range(4):
                cal = pd.concat([F[j] for j in range(4) if j != k])
                ev = F[k].dropna(subset=[col]).copy()
                cal = cal.dropna(subset=[col])
                hr = lambda x: x["ts_ist"].dt.hour
                isday = lambda x: (hr(x) >= d0) & (hr(x) < d1)
                q = conformal_q(cal[col].to_numpy(), cc["alpha"])
                qd, qn = (conformal_q(cal[isday(cal)][col].to_numpy(), cc["alpha"]), conformal_q(cal[~isday(cal)][col].to_numpy(), cc["alpha"]))
                ev["day"] = isday(ev)
                ev["cov"] = (ev[col] <= q).astype(float)
                ev["cov_dn"] = (ev[col] <= np.where(ev["day"], qd, qn)).astype(float)
                ev["low"] = ev["y"] <= ev["y_train_low"]
                qp = conformal_q(cal["ae_persistence"].dropna().to_numpy(), cc["alpha"])
                wide.append(2 * q)
                wide_p.append(2 * qp)
                per_fold.append(float(ev["cov"].mean()))
                rows.append(ev)
            E = pd.concat(rows, ignore_index=True)
            ctr[0] += 1
            cov = mean_ci(E, "cov", B, seed0 + ctr[0], lv)
            cd = lambda c: (E[E["day"]][c].mean(), E[~E["day"]][c].mean(), E[E["low"]][c].mean())
            a, b = cd("cov"), cd("cov_dn")
            dn_cov = E["cov_dn"].mean()
            ok_plain = 0.87 <= cov[0] <= 0.93 and min(a) >= 0.85
            ok_dn = 0.87 <= dn_cov <= 0.93 and min(b) >= 0.85
            verdict = "PASS (plain)" if ok_plain else ("PASS (day/night)" if ok_dn else "fail")
            decisions.append((v, h, verdict))
            f3 = lambda t: " / ".join(f"{x*100:.0f}%" for x in t)
            L.append(f"| {v} ({unit[v]}) | {hl[h]} | {pick} | {cov[0]*100:.1f}% [{cov[1]*100:.1f}, {cov[2]*100:.1f}] | ±{np.mean(wide)/2:.3f} | ±{np.mean(wide_p)/2:.3f} | {f3(a)} | {dn_cov*100:.1f}% | {f3(b)} | {min(per_fold)*100:.0f}%-{max(per_fold)*100:.0f}% | {verdict} |")
    n_pass = sum(1 for *_, vd in decisions if vd != "fail")
    L += ["", f"**{n_pass} of 9 cells pass** the pre-registered coverage rule ({cc['success']})."]
    return L


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def analyze(exp_id: str) -> str:
    import numpy as np
    import pandas as pd
    from aquatic_xai.alerts.evaluate import ap_ci, episode_stats, match_recall_threshold
    from aquatic_xai.alerts.labels import episode_onsets
    artifact_vol.reload()
    out = Path(ARTIFACT_MOUNT, "experiments", exp_id)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    cfg = man["config"]
    ac = cfg["alerts"]
    thr = ac["threshold_mg_l"]
    hl = {1: "15 min", 4: "1 h", 24: "6 h", 12: "3 h"}
    frames = {}
    for f in sorted((out / "alerts").glob("*.parquet")):
        r, w = f.stem.split("__")
        frames.setdefault(("seen" if r == "dev_future_seen_ponds" else "unseen", int(w[1:])), []).append(pd.read_parquet(f))
    D = {k: pd.concat(v, ignore_index=True) for k, v in frames.items()}
    Wn = {v: k for k, v in ac["windows"].items()}
    L = [f"# Phase 6 results, experiment `{exp_id}`", "",
         f"- Split `{man['split_version']}` (unchanged), features `{man['feature_version']}` + daily-v1, code commit `{man['code_git_sha'][:12]}`. Validation-side only; sealed test not used.",
         f"- Contract: `configs/phase6.yaml` (written before running). One round, no tuning.", ""]
    L += _conformal_report(cfg, hl)

    L += ["", f"## B. Low-oxygen early warning (event = any reading below {thr} mg/L within the next window), unseen ponds", "",
          "Average precision (AP; 1.0 is perfect, the event rate is the no-skill level). Higher is better.", "",
          "| window | event rate | model | 'same window yesterday' | 'trend' | 'current level' | model minus each baseline (99% interval) | verdict |", "|---|---|---|---|---|---|---|---|"]
    verdicts = {}
    for W in ac["windows"].values():
        d = D[("unseen", W)]
        r = ap_ci(d, "y", ["p_model", "s_yday", "s_trend", "s_level"], ac["bootstrap"]["B"], ac["bootstrap"]["seed"] + W, ac["bootstrap"]["level"])
        dd = r["diff"]
        ok = all(dd[s][1] > 0 for s in dd)
        verdicts[W] = ok
        L.append(f"| {Wn[W]} | {d['y'].mean()*100:.1f}% | {r['ap']['p_model']:.3f} | {r['ap']['s_yday']:.3f} | {r['ap']['s_trend']:.3f} | {r['ap']['s_level']:.3f} | "
                 + "; ".join(f"vs {n}: {dd[s][0]:+.3f} [{dd[s][1]:+.3f}, {dd[s][2]:+.3f}]" for s, n in (("s_yday", "yesterday"), ("s_trend", "trend"), ("s_level", "level"))) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{sum(verdicts.values())} of 3 windows pass** the pre-registered rule ({ac['success']})."]

    L += ["", "### Same models on seen ponds (context)", "", "| window | event rate | model AP | yesterday AP | trend AP | level AP |", "|---|---|---|---|---|---|"]
    from sklearn.metrics import average_precision_score as aps
    for W in ac["windows"].values():
        d = D[("seen", W)]
        L.append(f"| {Wn[W]} | {d['y'].mean()*100:.1f}% | " + " | ".join(f"{aps(d['y'].astype(int), d[c]):.3f}" for c in ("p_model", "s_yday", "s_trend", "s_level")) + " |")

    L += ["", "### Are the probabilities trustworthy? (unseen ponds; bins by predicted probability)", "",
          "| window | Brier score | predicted 0-10% -> actual | 10-30% | 30-50% | 50-70% | 70-90% | 90-100% |", "|---|---|---|---|---|---|---|---|"]
    for W in ac["windows"].values():
        d = D[("unseen", W)]
        bins = pd.cut(d["p_model"], [0, .1, .3, .5, .7, .9, 1.0001], include_lowest=True)
        g = d.groupby(bins, observed=False).agg(n=("y", "size"), rate=("y", "mean"), pm=("p_model", "mean"))
        L.append(f"| {Wn[W]} | {np.mean((d['p_model']-d['y'])**2):.3f} | " + " | ".join(f"{x.pm*100:.0f}% -> {x.rate*100:.0f}% (n={int(x.n)})" if x.n else "n/a" for x in g.itertuples()) + " |")

    # episodes, 6 h window
    sv, fv = man["split_version"], man["feature_version"]
    T = _data(sv, fv)[0]
    onsets = {p: episode_onsets(g, thr, ac["episode"]["quiet_slots"]) for p, g in T.groupby("pond", sort=False)}
    d = D[("unseen", 24)]
    lo, hi, op = ac["episode"]["lead_min_slots"], ac["episode"]["lead_max_slots"], ac["operating_point"]
    ms = episode_stats(d, onsets, "p_model", op, lo, hi)
    L += ["", f"### Episode-level view, 6 h window, unseen ponds (descriptive). Alert when P(event) >= {op}", "",
          f"An episode starts at the first reading below {thr} mg/L after 6 h without one; it is 'caught' if an alert fires 1-6 h earlier. "
          "Each baseline gets the strictest alert level that still catches at least as many episodes as the model (favours the baseline).", "",
          "| method | episodes | caught | recall | median warning (h) | pond-days with a false alarm | share of pond-days |", "|---|---|---|---|---|---|---|",
          f"| model (P >= {op}) | {ms['episodes']} | {ms['caught']} | {ms['recall']*100:.0f}% | {ms['median_lead_h']:.2f} | {ms['false_alarm_pond_days']} / {ms['pond_days']} | {ms['false_alarm_day_share']*100:.0f}% |"]
    for s, n in (("s_yday", "same window yesterday"), ("s_trend", "trend"), ("s_level", "current level")):
        t, st = match_recall_threshold(d, onsets, s, ms["recall"], lo, hi)
        L.append(f"| {n} | {st['episodes']} | {st['caught']} | {st['recall']*100:.0f}% | {st['median_lead_h']:.2f} | {st['false_alarm_pond_days']} / {st['pond_days']} | {st['false_alarm_day_share']*100:.0f}% |")
    L += ["", f"Onsets not counted because they fall outside these ponds' evaluation windows (no evaluation origin 1-6 h before them): {ms['excluded_no_origins']}. The {ms['episodes']} counted episodes are the ones inside the evaluation windows."]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, timeout=600)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"], capture_output=True, text=True)
    return r.stdout[-400:] + r.stderr[-400:]


@app.function(image=image, volumes=VOLUMES, timeout=120)
def versions() -> tuple[str, str]:
    data_vol.reload()
    return _latest("splits_sp-*.json", "split_version"), _latest("features_ft-*.json", "feature_version")


@app.local_entrypoint()
def show_prevalence():
    print(prevalence.remote())


@app.local_entrypoint()
def repro():
    sv, fv = versions.remote()
    print("REPRO:", json.dumps(repro_check.remote(sv, fv)))


@app.local_entrypoint()
def reanalyze(exp_id: str):
    report = analyze.remote(exp_id)
    Path(f"docs/experiments/{exp_id}_phase6_results.md").write_text(report, encoding="utf-8")
    print(report)


@app.local_entrypoint()
def main(git_sha: str = "unknown"):
    print(tests_remote.remote())
    sv, fv = versions.remote()
    chk = checks.remote(sv, fv)
    print("CHECKS:", json.dumps(chk))
    if not chk["split_identical"] or chk["label_rederivation"]["mismatches"] or chk["ydaymin_prefix_invariance"]["mismatches"]:
        raise SystemExit("STOP: split changed, labels misaligned, or the yesterday-window feature leaks")
    res = run_phase6.remote(git_sha, sv, fv)
    print("RUN:", json.dumps(res))
    if res["status"] == "written":
        print("REPRO:", json.dumps(repro_check.remote(sv, fv)))
    report = analyze.remote(res["experiment_id"])
    Path("docs/experiments").mkdir(parents=True, exist_ok=True)
    Path(f"docs/experiments/{res['experiment_id']}_phase6_results.md").write_text(report, encoding="utf-8")
    print(report)
