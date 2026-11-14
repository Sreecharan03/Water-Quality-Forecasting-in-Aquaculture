"""Phase 11: the sealed final test. Contract: configs/final_test.yaml (committed before any sealed row was read). RUN ONCE.

    modal run -m modal_jobs.phase11::smoke                         # exercises the code on DEVELOPMENT data only; prints no metrics
    modal run -m modal_jobs.phase11::final --git-sha <sha> --confirm "RUN THE SEALED TEST ONCE"
    modal run -m modal_jobs.phase11::reanalyze                     # rebuild the report from the stored result frames (touches no data)
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, VOLUMES, app, artifact_vol, image
from modal_jobs.loaders import load, versions as ds_versions

BUNDLE = Path(ARTIFACT_MOUNT, "models", "final_v1")
OUT = Path(ARTIFACT_MOUNT, "final_test")
CONFIRM = "RUN THE SEALED TEST ONCE"


def _evaluate(roles: list[str]) -> dict:
    """Apply the frozen bundle and baselines to the rows of the given roles. Returns forecast and alert frames."""
    from aquatic_xai.serving.engine import Engine
    from aquatic_xai.serving.final_eval import ALERT_WINDOWS, CELLS, alert_frame, eval_rows, forecast_frame, y_low_thresholds
    sv, fv = ds_versions("eluru")
    T, info, _ = load("eluru", sv, fv, alerts=True)
    eng = Engine(BUNDLE)
    rows = eval_rows(T, roles)
    low = y_low_thresholds(T, info)
    F = {f"{v}_{h}": forecast_frame(eng, T, rows, v, h, low[f"{v}_{h}"]) for v, h in CELLS}
    A = {str(W): alert_frame(eng, rows, W) for W in ALERT_WINDOWS}
    return {"F": F, "A": A, "ponds": sorted(rows["pond"].unique()), "n_rows": int(len(rows)), "info": info, "split": sv, "features": fv}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def smoke() -> dict:
    """Code check on development data (dev_val). The numbers are not looked at; only that every piece runs and returns sane shapes."""
    import numpy as np
    artifact_vol.reload()
    r = _evaluate(["dev_val"])
    sealed = set(r["info"]["sealed_ponds"])
    return {"ponds_used_are_all_development": not (set(r["ponds"]) & sealed), "n_rows": r["n_rows"],
            "forecast_cells": {k: int(len(v)) for k, v in r["F"].items()}, "alert_windows": {k: int(len(v)) for k, v in r["A"].items()},
            "any_nan_in_errors": bool(any(v["ae_chosen"].isna().any() for v in r["F"].values())),
            "probabilities_in_0_1": bool(all(((v["p_model"] >= 0) & (v["p_model"] <= 1)).all() for v in r["A"].values()))}


def _bundle_manifest_sha() -> str:
    return hashlib.sha256((BUNDLE / "manifest.json").read_bytes()).hexdigest()


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def run_final(git_sha: str, confirm: str) -> dict:
    from aquatic_xai.serving.bundle import verify_bundle
    artifact_vol.reload()
    if confirm != CONFIRM:
        return {"status": "refused", "reason": "confirmation phrase missing"}
    lock = OUT / "LOCK.json"
    if lock.exists():
        st = json.loads(lock.read_text(encoding="utf-8"))
        if st.get("status") == "completed":
            return {"status": "already_run", "lock": st}
        return {"status": "refused", "reason": "a previous attempt started but did not complete; a rerun needs a human decision", "lock": st}
    if not verify_bundle(BUNDLE):
        return {"status": "refused", "reason": "bundle files do not match their manifest hashes"}
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"status": "started", "started": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "git_sha": git_sha,
                                "bundle_manifest_sha256": _bundle_manifest_sha(), "contract": "configs/final_test.yaml"}, indent=2), encoding="utf-8")
    artifact_vol.commit()
    res = {}
    for name, roles in (("unseen_ponds_future", ["unseen_pond_test"]), ("seen_ponds_future", ["seen_pond_test"])):
        r = _evaluate(roles)
        res[name] = {"ponds": r["ponds"], "n_rows": r["n_rows"]}
        (OUT / name).mkdir(parents=True, exist_ok=True)
        for k, f in r["F"].items():
            buf = io.BytesIO()
            f.to_parquet(buf, index=False)
            (OUT / name / f"forecast_{k}.parquet").write_bytes(buf.getvalue())
        for k, f in r["A"].items():
            buf = io.BytesIO()
            f.to_parquet(buf, index=False)
            (OUT / name / f"alert_W{k}.parquet").write_bytes(buf.getvalue())
    st = json.loads(lock.read_text(encoding="utf-8"))
    st.update({"status": "completed", "completed": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "summary": res})
    lock.write_text(json.dumps(st, indent=2), encoding="utf-8")
    artifact_vol.commit()
    return {"status": "completed", "summary": res}


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def analyze_final(out_dir: str = str(OUT)) -> str:
    """Build the report from the stored result frames. Touches no data; the rules are those of configs/final_test.yaml."""
    import numpy as np
    import pandas as pd
    from aquatic_xai.alerts.calibrate import brier
    from aquatic_xai.alerts.evaluate import ap_ci, episode_stats, match_recall_threshold
    from aquatic_xai.alerts.labels import episode_onsets
    from aquatic_xai.experiments.evaluate import improvement_ci, mean_ci
    from aquatic_xai.serving.final_eval import ALERT_WINDOWS, CELLS
    artifact_vol.reload()
    OUT_ = Path(out_dir)
    lock = json.loads((OUT_ / "LOCK.json").read_text(encoding="utf-8"))
    assert lock["status"] == "completed"
    man = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    B, seed0, lv = 2000, 20261113, 99
    ctr = [0]

    def nxt():
        ctr[0] += 1
        return seed0 + ctr[0]

    def rd(group, name):
        return pd.read_parquet(OUT_ / group / name)
    hl = {1: "15 min", 4: "1 h", 24: "6 h"}
    unit = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
    nm = {"DO": "Oxygen", "pH": "pH", "Temp": "Temperature"}
    meth = {"model": "trained model", "same_as_now": "same as now", "yesterday": "same time yesterday"}

    def fmt(t, pct=False, d=3):
        e, lo, hi, _ = t
        return f"{e*100:+.1f}% [{lo*100:+.1f}, {hi*100:+.1f}]" if pct else f"{e:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"

    L = ["# Phase 11 results: the sealed final test (run once)", "",
         f"- Contract `configs/final_test.yaml`, committed before any sealed row was read. Bundle `{man['bundle_version']}` (manifest sha256 `{lock['bundle_manifest_sha256'][:16]}...`), code commit `{lock['git_sha'][:12]}`.",
         f"- Run started {lock['started']}, completed {lock['completed']}. **One run.** Intervals: {lv}% blocked bootstrap (blocks = pond x calendar day).",
         f"- Sealed (never-seen) ponds: {', '.join(lock['summary']['unseen_ponds_future']['ponds'])}; {lock['summary']['unseen_ponds_future']['n_rows']:,} test-window origins. "
         f"Development ponds, test window: {lock['summary']['seen_ponds_future']['n_rows']:,} origins.",
         "- Models were trained on development ponds, training + validation windows only. Nothing was refit, tuned or selected on the test.", ""]
    # ---------------- forecasts
    L += ["## A. Forecast accuracy on the sealed ponds (average miss, MAE)", "",
          "| target | ahead | method used by the app | app (99% interval) | 'same as now' | 'same time yesterday' | validation MAE of the app method | vs 'same as now' | vs 'same time yesterday' | verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    passes, model_cells = 0, 0
    rangerows = []
    for v, h in CELLS:
        key = f"{v}_{h}"
        c = man["cells"][key]
        d = rd("unseen_ponds_future", f"forecast_{key}.parquet")
        mc = mean_ci(d, "ae_chosen", B, nxt(), lv)
        mp = mean_ci(d, "ae_persistence", B, nxt(), lv)
        ms = mean_ci(d.dropna(subset=["ae_seasonal_naive"]), "ae_seasonal_naive", B, nxt(), lv)
        ia = improvement_ci(d, "ae_chosen", "ae_persistence", B, nxt(), lv)
        ib = improvement_ci(d, "ae_chosen", "ae_seasonal_naive", B, nxt(), lv)
        if c["method"] == "model":
            model_cells += 1
            ok = ia[1] > 0 and ib[1] > 0
            passes += ok
            verdict = "**PASS**" if ok else "**fail**"
        else:
            verdict = "no claim (plain guess)"
        L.append(f"| {nm[v]} ({unit[v]}) | {hl[h]} | {meth[c['method']]} | {fmt(mc)} | {fmt(mp)} | {fmt(ms)} | {c['mae_method']:.3f} | {fmt(ia, True)} | {fmt(ib, True)} | {verdict} |")
        rangerows.append((v, h, d, c))
    L += ["", f"**{passes} of {model_cells} model cells pass** (rule F1: lower end of the 99% interval above 0 against both plain guesses). "
              + ("All five pass." if passes == model_cells else "Forecasting is therefore **not** called validated; see the failed cells above.")]
    # seen ponds, context
    L += ["", "### Context: development ponds, test window (ponds the models saw, later days)", "",
          "| target | ahead | app | 'same as now' | 'same time yesterday' |", "|---|---|---|---|---|"]
    for v, h in CELLS:
        d = rd("seen_ponds_future", f"forecast_{v}_{h}.parquet")
        L.append(f"| {nm[v]} | {hl[h]} | {fmt(mean_ci(d, 'ae_chosen', B, nxt(), lv))} | {fmt(mean_ci(d, 'ae_persistence', B, nxt(), lv))} | {fmt(mean_ci(d.dropna(subset=['ae_seasonal_naive']), 'ae_seasonal_naive', B, nxt(), lv))} |")
    # ---------------- ranges
    L += ["", "## B. Do the 'likely between' ranges hold? (target 90%, sealed ponds)", "",
          "| target | ahead | coverage (99% interval) | day / night / low-value coverage | rows in the low-value group | per-pond coverage (min-max) | verdict |", "|---|---|---|---|---|---|---|"]
    n_r = 0
    for v, h, d, c in rangerows:
        cov = mean_ci(d, "cover", B, nxt(), lv)
        dd = (d[d["day"]]["cover"].mean(), d[~d["day"]]["cover"].mean(), d[d["low"]]["cover"].mean() if d["low"].any() else float("nan"))
        pp = d.groupby("pond")["cover"].mean()
        ok = 0.87 <= cov[0] <= 0.93 and np.nanmin(dd) >= 0.85
        n_r += ok
        L.append(f"| {nm[v]} | {hl[h]} | {cov[0]*100:.1f}% [{cov[1]*100:.1f}, {cov[2]*100:.1f}] | " + " / ".join(f"{x*100:.0f}%" for x in dd) + f" | {int(d['low'].sum())} | {pp.min()*100:.0f}%-{pp.max()*100:.0f}% | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{n_r} of 9 range cells pass** (rule R1)."]
    # ---------------- alert
    L += ["", "## C. Low-oxygen chance (below 2 mg/L), sealed ponds", "",
          "| window | event rate | model AP | yesterday AP | trend AP | level AP | model minus each baseline (99% interval) | verdict |", "|---|---|---|---|---|---|---|---|"]
    wn = {4: "next hour", 12: "next 3 hours", 24: "next 6 hours"}
    n_a, A = 0, {}
    for W in ALERT_WINDOWS:
        d = rd("unseen_ponds_future", f"alert_W{W}.parquet")
        A[W] = d
        r = ap_ci(d, "y", ["p_model", "s_yday", "s_trend", "s_level"], 1000, seed0 + W, lv)
        dd = r["diff"]
        ok = all(dd[s][1] > 0 for s in dd)
        n_a += ok
        L.append(f"| {wn[W]} | {d['y'].mean()*100:.1f}% | {r['ap']['p_model']:.3f} | {r['ap']['s_yday']:.3f} | {r['ap']['s_trend']:.3f} | {r['ap']['s_level']:.3f} | "
                 + "; ".join(f"vs {n}: {dd[s][0]:+.3f} [{dd[s][1]:+.3f}, {dd[s][2]:+.3f}]" for s, n in (("s_yday", "yesterday"), ("s_trend", "trend"), ("s_level", "level"))) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{n_a} of 3 windows pass** (rule A1)."]
    L += ["", "### Calibration of the app's percentages (rule A2)", "", "| window | Brier raw | Brier calibrated | bins (calibrated -> actual, n) | criterion |", "|---|---|---|---|---|"]
    n_c = 0
    for W in ALERT_WINDOWS:
        d = A[W]
        bins = pd.cut(d["p_cal"], [0, .1, .3, .5, .7, .9, 1.0001], include_lowest=True)
        g = d.groupby(bins, observed=False).agg(n=("y", "size"), rate=("y", "mean"), pm=("p_cal", "mean"))
        big = g[g["n"] >= 100]
        ok = brier(d["p_cal"], d["y"]) < brier(d["p_model"], d["y"]) and bool(((big["pm"] - big["rate"]).abs() <= 0.10).all())
        n_c += ok
        L.append(f"| {wn[W]} | {brier(d['p_model'], d['y']):.4f} | {brier(d['p_cal'], d['y']):.4f} | " + "; ".join(f"{x.pm*100:.0f}% -> {x.rate*100:.0f}% ({int(x.n)})" for x in g.itertuples() if x.n) + f" | {'PASS' if ok else 'fail'} |")
    L += ["", f"**{n_c} of 3 windows pass** the calibration criterion."]
    # episodes
    sv, fv = ds_versions("eluru")
    T, info, _ = load("eluru", sv, fv, alerts=False)
    onsets = {p: episode_onsets(g[["grid_idx", "DO_cur"]], 2.0, 24) for p, g in T.groupby("pond", sort=False)}
    d = A[24]
    high = man["alerts"]["24"]["high_cal"]
    ms = episode_stats(d, onsets, "p_cal", high, 4, 24)
    L += ["", f"### Episodes, 6 h window (descriptive, rule A3): the app says 'High chance' at a calibrated {high*100:.0f}% or more", "",
          "| method | episodes | caught | recall | median warning (h) | pond-days with a false alarm | share |", "|---|---|---|---|---|---|---|",
          f"| app | {ms['episodes']} | {ms['caught']} | {ms['recall']*100:.0f}% | {ms['median_lead_h']:.2f} | {ms['false_alarm_pond_days']} / {ms['pond_days']} | {ms['false_alarm_day_share']*100:.0f}% |"]
    t, sb = match_recall_threshold(d, onsets, "s_yday", ms["recall"], 4, 24)
    L.append(f"| same window yesterday (strictest level matching the app's recall; favours it) | {sb['episodes']} | {sb['caught']} | {sb['recall']*100:.0f}% | {sb['median_lead_h']:.2f} | {sb['false_alarm_pond_days']} / {sb['pond_days']} | {sb['false_alarm_day_share']*100:.0f}% |")
    # summary
    L += ["", "## Summary against the pre-registered rules", "", "| rule | result |", "|---|---|",
          f"| F1 model cells beating both plain guesses (99%) | {passes} of {model_cells} |", f"| R1 range cells with valid coverage | {n_r} of 9 |",
          f"| A1 alert beats all three baselines | {n_a} of 3 windows |", f"| A2 alert percentages calibrated | {n_c} of 3 windows |"]
    md = "\n".join(L)
    (OUT_ / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def rehearse() -> dict:
    """Run the full evaluation + analysis path on DEVELOPMENT rows (dev_val) in a separate folder, to catch bugs before the sealed run.
    The numbers (in-sample for the bundle) are discarded."""
    import shutil
    artifact_vol.reload()
    rh = Path(ARTIFACT_MOUNT, "final_test_rehearsal")
    if rh.exists():
        shutil.rmtree(rh)
    r = _evaluate(["dev_val"])
    for g in ("unseen_ponds_future", "seen_ponds_future"):
        (rh / g).mkdir(parents=True, exist_ok=True)
        for k, f in r["F"].items():
            f.to_parquet(rh / g / f"forecast_{k}.parquet", index=False)
        for k, f in r["A"].items():
            f.to_parquet(rh / g / f"alert_W{k}.parquet", index=False)
    (rh / "LOCK.json").write_text(json.dumps({"status": "completed", "started": "rehearsal", "completed": "rehearsal", "git_sha": "rehearsal000000",
                                              "bundle_manifest_sha256": _bundle_manifest_sha(),
                                              "summary": {"unseen_ponds_future": {"ponds": r["ponds"], "n_rows": r["n_rows"]}, "seen_ponds_future": {"ponds": r["ponds"], "n_rows": r["n_rows"]}}}), encoding="utf-8")
    artifact_vol.commit()
    md = analyze_final.remote(str(rh))
    return {"report_chars": len(md), "sections": [l for l in md.splitlines() if l.startswith("## ")], "rows_in_forecast_table": sum(1 for l in md.splitlines() if l.startswith("| Oxygen") or l.startswith("| pH") or l.startswith("| Temperature"))}


@app.local_entrypoint()
def rehearsal():
    print("REHEARSAL:", json.dumps(rehearse.remote(), indent=1))


@app.local_entrypoint()
def smoke_run():
    print("SMOKE:", json.dumps(smoke.remote(), indent=1))


@app.local_entrypoint()
def final(git_sha: str, confirm: str = ""):
    res = run_final.remote(git_sha, confirm)
    print("RUN:", json.dumps(res, indent=1)[:1500])
    if res["status"] == "completed":
        report = analyze_final.remote()
        Path("docs/experiments").mkdir(parents=True, exist_ok=True)
        Path("docs/experiments/final_test_report.md").write_text(report, encoding="utf-8")
        print(report)


@app.local_entrypoint()
def reanalyze():
    report = analyze_final.remote()
    Path("docs/experiments/final_test_report.md").write_text(report, encoding="utf-8")
    print(report)
