"""Phases 9 and 10: build the model bundle for the app and test the service (on Modal; nothing is deployed publicly here).

    modal run -m modal_jobs.phase10::build --git-sha <sha>      # train final models on dev_train + dev_val of the DEVELOPMENT ponds, write the bundle
    modal run -m modal_jobs.phase10::verify --git-sha <sha>     # service tests: bundle integrity, train/serve parity, API behaviour, latency

The sealed ponds and the test window are never read here.
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image
from modal_jobs.loaders import feature_cfg, latest, load, versions as ds_versions, yaml_cfg

BUNDLE = Path(ARTIFACT_MOUNT, "models", "final_v1")
PHASE5B = "exp-1e0c9c9e8164"
PHASE6B = "exp-932480b9ca47"
SEEDS = [0, 1, 2]


@app.function(image=image, volumes=VOLUMES, timeout=3600, cpu=2.0)
def build_bundle(git_sha: str, force: bool = False) -> dict:
    import datetime
    import lightgbm as lgb
    import numpy as np
    import pandas as pd
    from aquatic_xai.features.daily import daily_specs
    from aquatic_xai.features.dictionary import feature_specs
    from aquatic_xai.models.anchored import add_anchor_gap, anchor_for
    from aquatic_xai.models.tabular import make_model
    from aquatic_xai.serving.bundle import (ALERT_WINDOWS, DAYNIGHT_CELLS, EXPLAIN_VALIDATED, PLAN, alert_columns, model_columns, save_booster,
                                            verify_bundle, write_manifest)
    from aquatic_xai.uncertainty.conformal import conformal_q
    import shutil
    from aquatic_xai.serving.engine import INPUT_DECIMALS
    if force and BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    if (BUNDLE / "manifest.json").exists():
        return {"status": "already_exists", "bundle": str(BUNDLE), "verified": verify_bundle(BUNDLE)}
    artifact_vol.reload()
    sv, fv = ds_versions("eluru")
    T, info, _ = load("eluru", sv, fv, alerts=True)
    fcfg, params = feature_cfg("eluru"), yaml_cfg("models.yaml")["models"]["lightgbm"]
    base = (T["role"].isin(["dev_train", "dev_val"])) & T["pond"].isin(info["dev_ponds"]) & ~T["is_warmup"]
    assert not T.loc[base, "pond"].isin(info["sealed_ponds"]).any() and not (T.loc[base, "role"].isin(["unseen_pond_test", "seen_pond_test"])).any()
    exp = Path(ARTIFACT_MOUNT, "experiments")
    cells, counts = {}, {}
    for (var, h), (method, anchor) in PLAN.items():
        cell = {"variable": var, "h": h, "method": method, "anchor": anchor, "explain_validated": EXPLAIN_VALIDATED.get((var, h), True)}
        if method == "model":
            ycol, ccol = f"y_{var}_h{h}", f"{var}_cur"
            tr = T[base & T[ycol].notna() & T[ccol].notna()]
            cols = model_columns(fcfg, var, h, anchor)
            a_tr, _ = anchor_for(tr, var, h, anchor)
            X = tr[cols].to_numpy(dtype=float)
            if anchor == "yesterday":
                X = np.column_stack([X, add_anchor_gap(tr, var, a_tr)])
            X = np.round(X, INPUT_DECIMALS)            # same rounding as the serving engine
            files = []
            for s in SEEDS:
                m = make_model("lightgbm", params, s).fit(X, tr[ycol].to_numpy(dtype=float) - a_tr)
                f = f"{var}_{h}_s{s}.txt"
                save_booster(m, BUNDLE / "models" / f)
                files.append(f)
            cell.update({"columns": cols, "files": files})
            counts[f"{var}_{h}"] = int(len(tr))
        # ranges and honest test numbers, from the Phase 5b predictions on ponds the model never saw (4 held-out pond groups)
        F = pd.concat([pd.read_parquet(exp / PHASE5B / "preds" / f"dev_future_unseen_fold{k}__{var}__h{h}.parquet") for k in range(4)], ignore_index=True)
        col = {"model": "ae_anch_blind", "same_as_now": "ae_persistence", "yesterday": "ae_seasonal_naive"}[method]
        F = F.dropna(subset=[col])
        hr = pd.to_datetime(F["ts_ist"]).dt.hour
        isday = (hr >= 6) & (hr < 18)
        cell["range"] = {"use": "daynight" if (var, h) in DAYNIGHT_CELLS else "plain", "plain": conformal_q(F[col].to_numpy(), 0.10),
                         "day": conformal_q(F.loc[isday, col].to_numpy(), 0.10), "night": conformal_q(F.loc[~isday, col].to_numpy(), 0.10)}
        cell["mae_method"] = float(F[col].mean())
        cell["mae_simple"] = float(min(F["ae_persistence"].mean(), F["ae_seasonal_naive"].dropna().mean()))
        cells[f"{var}_{h}"] = cell
    cal = json.loads((exp / PHASE6B / "calibrators.json").read_text(encoding="utf-8"))
    alerts = {}
    for W, name in ALERT_WINDOWS.items():
        lab = f"lab_W{W}"
        tr = T[base & T[lab].notna() & T["DO_cur"].notna()]
        cols = alert_columns(fcfg, W)
        files = []
        for s in SEEDS:
            m = lgb.LGBMClassifier(**params, random_state=s, n_jobs=2, verbose=-1).fit(np.round(tr[cols].to_numpy(dtype=float), INPUT_DECIMALS), tr[lab].to_numpy(dtype=int))
            f = f"A_{W}_s{s}.txt"
            save_booster(m, BUNDLE / "models" / f)
            files.append(f)
        alerts[str(W)] = {"columns": cols, "files": files, "calib": cal["calibrators"][name], "explain_validated": True,
                          "high_cal": float(cal["alert_level_calibrated_6h"]) if W == 24 else 0.5}
        counts[f"A_{W}"] = int(len(tr))
    evid = ["We tested on ponds the computer had never seen, using later days than it learned from. A final locked test on sealed ponds is planned and has not been used yet, so these are practice-test results."]
    for key, c in cells.items():
        if c["method"] == "model":
            u = {"DO": "mg/L", "pH": "", "Temp": "°C"}[c["variable"]]
            when = {1: "15 minutes", 4: "1 hour", 24: "6 hours"}[c["h"]]
            nm = {"DO": "Oxygen", "pH": "pH", "Temp": "Water temperature"}[c["variable"]]
            evid.append(f"{nm}, {when} ahead: the model missed by about {c['mae_method']:.2f} {u}".rstrip() + f"; the best plain guess missed by about {c['mae_simple']:.2f} {u}.".replace(" .", "."))
    evid += ["For pH at every distance, and for water temperature 15 minutes ahead, the trained models did not clearly beat a plain guess, so the app uses the plain guess and says so.",
             "The \"likely between\" ranges contained the real value about 9 times out of 10 on ponds the computer had never seen.",
             "The chance of very low oxygen ranks risky moments better than three simple rules, but it is experimental: at the level we tested it still raised a false alarm on about 2 of every 3 days, no better than looking at what happened at the same time yesterday.",
             "We tested the reasons shown for each answer for stability. 9 of 11 passed; the oxygen 15-minute reasons are shown with a warning."]
    limits = ["Tested on one region (Eluru, India) in a cool season, about 7 weeks of data from 13 ponds. It may not suit other places, seasons or pond types.",
              "A second test on a very different place (salt-marsh ponds in the USA) showed the same method helped with temperature but not with oxygen. Do not assume it works everywhere.",
              "Oxygen 6 hours ahead can be off by several mg/L; the range shown says how much.",
              "It cannot see feeding, aeration, weather or stocking, which strongly affect oxygen.",
              "Sensors fail. We ignore readings of exactly 0, impossible values and stuck sensors, but we cannot catch every bad reading.",
              "Explanations describe how the computer model reasons. They are not proof of what is happening in your pond."]
    tr_all = T[base]
    training_range = {v: {"min": float(tr_all[f"{v}_cur"].min()), "max": float(tr_all[f"{v}_cur"].max()), "p1": float(tr_all[f"{v}_cur"].quantile(0.01)),
                          "p99": float(tr_all[f"{v}_cur"].quantile(0.99))} for v in ("DO", "pH", "Temp")}
    write_manifest(BUNDLE, {"bundle_version": "final_v1", "created": datetime.date.today().isoformat(), "code_git_sha": git_sha,
                            "trained_on": "development ponds, training and validation windows only (sealed ponds and test windows never used)",
                            "split_version": sv, "feature_version": fv, "training_rows": counts, "features_cfg": fcfg, "day_steps": 96, "day_hours": [6, 18],
                            "alert_threshold_mg_l": 2.0, "cells": cells, "alerts": alerts, "evidence": evid, "limits": limits,
                            "training_range": training_range, "range_source": {"experiment": PHASE5B, "alert_calibrators": PHASE6B}, "lightgbm": lgb.__version__})
    artifact_vol.commit()
    return {"status": "written", "bundle": str(BUNDLE), "verified": verify_bundle(BUNDLE), "training_rows": counts}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def verify_service(git_sha: str, bundle: str = "final_v1") -> dict:
    import time
    import numpy as np
    import pandas as pd
    from fastapi.testclient import TestClient
    from app.main import create_app
    from aquatic_xai.serving.bundle import verify_bundle
    from aquatic_xai.serving.engine import Engine
    artifact_vol.reload()
    sv, fv = ds_versions("eluru")
    bpath = Path(ARTIFACT_MOUNT, "models", bundle)
    res = {"bundle": bundle, "bundle_integrity_hashes_match": verify_bundle(bpath)}
    eng = Engine(bpath)
    client = TestClient(create_app(str(bpath)))
    # ---- train/serve parity: the service, fed only readings, must equal the offline pipeline row for the same moment
    T, info, _ = load("eluru", sv, fv, alerts=True)
    rng = np.random.RandomState(20261114)
    checked, skipped, worst_val, worst_p = 0, 0, 0.0, 0.0
    ponds = sorted(info["dev_ponds"])[:4]
    for pond in ponds:
        P = T[T["pond"] == pond].reset_index(drop=True)
        cand = P.index[(P["role"] == "dev_val") & ~P["is_warmup"] & P["DO_cur"].notna() & (P["grid_idx"] >= 160)].to_numpy()
        for i in np.sort(rng.choice(cand, size=min(6, len(cand)), replace=False)):
            g = int(P.loc[i, "grid_idx"])
            w = P[(P["grid_idx"] >= g - 139) & (P["grid_idx"] <= g)]
            if len(w) < 120:
                skipped += 1
                continue
            csv = pd.DataFrame({"time": w["ts_ist"].dt.strftime("%Y-%m-%d %H:%M:%S"), "oxygen": w["DO_cur"].to_numpy(), "pH": w["pH_cur"].to_numpy(),
                                "temperature": w["Temp_cur"].to_numpy()}).to_csv(index=False)
            r = client.post("/api/forecast", json={"csv_text": csv})
            if r.status_code != 200:
                skipped += 1
                continue
            out = r.json()["result"]
            row = P.loc[i].to_dict()
            hour = int(pd.Timestamp(P.loc[i, "ts_ist"]).hour)
            for v in ("DO", "pH", "Temp"):
                for item in out["forecasts"][v]:
                    if item["status"] != "ok":
                        continue
                    off = eng._cell(v, item["ahead_steps"], row, hour, None)
                    worst_val = max(worst_val, abs(item["value"] - off["value"]), abs(item["low"] - off["low"]), abs(item["high"] - off["high"]))
            off_alert = eng._alert(row, None)["windows"]
            for a, b in zip(out["alert"]["windows"], off_alert):
                if a["status"] == "ok":
                    worst_p = max(worst_p, abs(a["p_raw"] - b["p_raw"]))
            checked += 1
    res["parity"] = {"moments_checked": checked, "skipped": skipped, "max_abs_diff_forecast_value_or_range": worst_val, "max_abs_diff_alert_probability": worst_p,
                     "pass": bool(checked >= 15 and worst_val < 2e-3 and worst_p < 2e-4)}
    # ---- API on the made-up example, and latency
    ex = client.get("/api/example").json()["csv"]
    r = client.post("/api/forecast", json={"pond_name": "Example", "csv_text": ex})
    j = r.json()
    res["example_forecast"] = {"status": r.status_code, "oxygen_1h": j["result"]["forecasts"]["DO"][1]["value_text"], "range": j["result"]["forecasts"]["DO"][1]["range_text"],
                               "alert_windows": [(w["window"], w.get("percent"), w.get("level")) for w in j["result"]["alert"]["windows"]],
                               "all_ok": all(x["status"] == "ok" for v in j["result"]["forecasts"].values() for x in v)}
    # a pond from a very different climate (salt-marsh-like temperatures) must be refused, not guessed
    cold = pd.read_csv(__import__("io").StringIO(ex))
    cold["temperature"] = cold["temperature"] - 15.0
    jc = client.post("/api/forecast", json={"csv_text": cold.to_csv(index=False)}).json()
    res["out_of_range_guard"] = {"temperature_forecasts_refused": all(x["status"] == "no_forecast" for x in jc["result"]["forecasts"]["Temp"]),
                                 "oxygen_still_forecast": all(x["status"] == "ok" for x in jc["result"]["forecasts"]["DO"])}
    times = []
    for _ in range(25):
        t0 = time.perf_counter()
        client.post("/api/forecast", json={"csv_text": ex})
        times.append(time.perf_counter() - t0)
    res["latency_seconds"] = {"p50": round(float(np.percentile(times, 50)), 3), "p95": round(float(np.percentile(times, 95)), 3), "pass": bool(np.percentile(times, 95) < 1.0)}
    res["all_pass"] = bool(res["bundle_integrity_hashes_match"] and res["parity"]["pass"] and res["example_forecast"]["all_ok"] and res["latency_seconds"]["pass"]
                           and res["out_of_range_guard"]["temperature_forecasts_refused"] and res["out_of_range_guard"]["oxygen_still_forecast"])
    return res


@app.function(image=image, timeout=900)
def tests_remote(k: str = "") -> str:
    import subprocess
    cmd = ["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"] + (["-k", k, "-x", "--tb=short"] if k else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout[-3500:] if k else r.stdout[-500:]) + r.stderr[-500:]


@app.local_entrypoint()
def build(git_sha: str = "unknown", force: bool = False):
    print(tests_remote.remote())
    print("BUNDLE:", json.dumps(build_bundle.remote(git_sha, force)))


@app.local_entrypoint()
def tests_only(k: str = ""):
    print(tests_remote.remote(k))


@app.local_entrypoint()
def verify(git_sha: str = "unknown", bundle: str = "final_v1"):
    print("VERIFY:", json.dumps(verify_service.remote(git_sha, bundle), indent=1))


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def debug_parity() -> str:
    """Find which input columns differ between the service's feature row and the offline feature row for the same moment."""
    import numpy as np
    import pandas as pd
    from aquatic_xai.serving import ingest
    from aquatic_xai.serving.engine import Engine
    artifact_vol.reload()
    sv, fv = ds_versions("eluru")
    eng = Engine(BUNDLE)
    T, info, _ = load("eluru", sv, fv, alerts=True)
    rng = np.random.RandomState(20261114)
    L = []
    for pond in sorted(info["dev_ponds"])[:2]:
        P = T[T["pond"] == pond].reset_index(drop=True)
        cand = P.index[(P["role"] == "dev_val") & ~P["is_warmup"] & P["DO_cur"].notna() & (P["grid_idx"] >= 160)].to_numpy()
        for i in np.sort(rng.choice(cand, size=4, replace=False)):
            g = int(P.loc[i, "grid_idx"])
            w = P[(P["grid_idx"] >= g - 139) & (P["grid_idx"] <= g)]
            csv = pd.DataFrame({"time": w["ts_ist"].dt.strftime("%Y-%m-%d %H:%M:%S"), "oxygen": w["DO_cur"].to_numpy(), "pH": w["pH_cur"].to_numpy(), "temperature": w["Temp_cur"].to_numpy()}).to_csv(index=False)
            grid, issues, summary = ingest.prepare(ingest.parse_text(csv))
            row = eng._row(grid)
            off = P.loc[i].to_dict()
            bad = []
            for c in {c for cell in eng.m["cells"].values() for c in cell.get("columns", [])} | {c for a in eng.m["alerts"].values() for c in a["columns"]}:
                a, b = row.get(c, np.nan), off.get(c, np.nan)
                if not ((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9):
                    bad.append((c, a, b))
            L.append(f"{pond} g={g} rows_in_window={len(w)} grid_len={len(grid)} diffs={len(bad)} {bad[:6]}")
    return "\n".join(L)


@app.local_entrypoint()
def debug():
    print(debug_parity.remote())


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def debug_parity2() -> str:
    import numpy as np
    import pandas as pd
    from fastapi.testclient import TestClient
    from app.main import create_app
    from aquatic_xai.serving.engine import Engine
    artifact_vol.reload()
    sv, fv = ds_versions("eluru")
    eng = Engine(BUNDLE)
    client = TestClient(create_app(str(BUNDLE)))
    T, info, _ = load("eluru", sv, fv, alerts=True)
    rng = np.random.RandomState(20261114)
    L = []
    for pond in sorted(info["dev_ponds"])[:4]:
        P = T[T["pond"] == pond].reset_index(drop=True)
        cand = P.index[(P["role"] == "dev_val") & ~P["is_warmup"] & P["DO_cur"].notna() & (P["grid_idx"] >= 160)].to_numpy()
        for i in np.sort(rng.choice(cand, size=min(6, len(cand)), replace=False)):
            g = int(P.loc[i, "grid_idx"])
            w = P[(P["grid_idx"] >= g - 139) & (P["grid_idx"] <= g)]
            csv = pd.DataFrame({"time": w["ts_ist"].dt.strftime("%Y-%m-%d %H:%M:%S"), "oxygen": w["DO_cur"].to_numpy(), "pH": w["pH_cur"].to_numpy(), "temperature": w["Temp_cur"].to_numpy()}).to_csv(index=False)
            r = client.post("/api/forecast", json={"csv_text": csv})
            if r.status_code != 200:
                L.append(f"{pond} g={g} status={r.status_code} {r.json()}")
                continue
            out = r.json()["result"]
            row = P.loc[i].to_dict()
            hour = int(pd.Timestamp(P.loc[i, "ts_ist"]).hour)
            for v in ("DO", "pH", "Temp"):
                for item in out["forecasts"][v]:
                    if item["status"] != "ok":
                        L.append(f"{pond} g={g} {v} h{item['ahead_steps']} service says {item['status']}: {item.get('reason')}")
                        continue
                    off = eng._cell(v, item["ahead_steps"], row, hour, None)
                    d = max(abs(item["value"] - off["value"]), abs(item["low"] - off["low"]), abs(item["high"] - off["high"]))
                    if d > 1e-3:
                        L.append(f"{pond} g={g} {v} h{item['ahead_steps']} service {item['value']} [{item['low']},{item['high']}] offline {off['value']} [{off['low']},{off['high']}] hour={hour} note={item.get('note')} / {off.get('note')}")
    return "\n".join(L) or "no differences"


@app.local_entrypoint()
def debug2():
    print(debug_parity2.remote())


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def debug_parity3() -> str:
    import numpy as np
    import pandas as pd
    from aquatic_xai.serving import ingest
    from aquatic_xai.serving.engine import Engine
    artifact_vol.reload()
    sv, fv = ds_versions("eluru")
    eng = Engine(BUNDLE)
    T, info, _ = load("eluru", sv, fv, alerts=True)
    pond = "ara2_0677080b"
    P = T[T["pond"] == pond].reset_index(drop=True)
    i = P.index[P["grid_idx"] == 3267][0]
    g = 3267
    w = P[(P["grid_idx"] >= g - 139) & (P["grid_idx"] <= g)]
    csv = pd.DataFrame({"time": w["ts_ist"].dt.strftime("%Y-%m-%d %H:%M:%S"), "oxygen": w["DO_cur"].to_numpy(), "pH": w["pH_cur"].to_numpy(), "temperature": w["Temp_cur"].to_numpy()}).to_csv(index=False)
    grid, issues, summary = ingest.prepare(ingest.parse_text(csv))
    row = eng._row(grid)
    off = P.loc[i].to_dict()
    c = eng.m["cells"]["Temp_4"]
    xs = eng._vec(c["columns"], row)
    xo = eng._vec(c["columns"], off)
    L = [f"X max abs diff service vs offline: {np.nanmax(np.abs(xs - xo))}; nan same: {np.array_equal(np.isnan(xs), np.isnan(xo))}"]
    ps = [b.predict(xs[None, :])[0] for b in eng._boosters["Temp_4"]]
    po = [b.predict(xo[None, :])[0] for b in eng._boosters["Temp_4"]]
    L.append(f"service preds {ps}  offline preds {po}")
    L.append(f"cur service {row['Temp_cur']} offline {off['Temp_cur']}; grid last ts {grid['ts'].iloc[-1]} P ts {P.loc[i, 'ts_ist']}")
    # compare full vector columns that differ at any tolerance
    diffs = [(n, a, b) for n, a, b in zip(c["columns"], xs, xo) if not ((np.isnan(a) and np.isnan(b)) or a == b)]
    L.append(f"exactly-different columns: {diffs[:8]}")
    return "\n".join(L)


@app.local_entrypoint()
def debug3():
    print(debug_parity3.remote())


@app.function(image=image, volumes=VOLUMES, timeout=600, cpu=2.0)
def example_json() -> str:
    """Full API response for the made-up example pond (used to preview the UI; contains no real data)."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    artifact_vol.reload()
    c = TestClient(create_app(str(BUNDLE)))
    ex = c.get("/api/example").json()
    out = {"example": ex, "forecast": c.post("/api/forecast", json={"pond_name": "Example pond (made-up numbers)", "csv_text": ex["csv"]}).json(), "about": c.get("/api/about").json()}
    return json.dumps(out)


@app.local_entrypoint()
def save_example(path: str):
    Path(path).write_text(example_json.remote(), encoding="utf-8")
    print("saved", path)


BUNDLE2 = Path(ARTIFACT_MOUNT, "models", "final_v2")


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def build_v2(git_sha: str, force: bool = False) -> dict:
    """final_v2 = final_v1 with the two 6-hour model cells that FAILED the sealed final test (oxygen, temperature) switched to the plain guess
    'same time yesterday' (the fallback rule pre-registered in Phase 5b), and the evidence text updated to the final test. final_v1 is not touched."""
    import shutil
    import pandas as pd
    from aquatic_xai.serving.bundle import verify_bundle, write_manifest
    from aquatic_xai.uncertainty.conformal import conformal_q
    artifact_vol.reload()
    if force and BUNDLE2.exists():
        shutil.rmtree(BUNDLE2)
    if (BUNDLE2 / "manifest.json").exists():
        return {"status": "already_exists", "verified": verify_bundle(BUNDLE2)}
    shutil.copytree(BUNDLE, BUNDLE2)
    m = json.loads((BUNDLE2 / "manifest.json").read_text(encoding="utf-8"))
    exp = Path(ARTIFACT_MOUNT, "experiments")
    for key, (var, h) in {"DO_24": ("DO", 24), "Temp_24": ("Temp", 24)}.items():
        old = m["cells"][key]
        for f in old.get("files", []):
            (BUNDLE2 / "models" / f).unlink()
        F = pd.concat([pd.read_parquet(exp / PHASE5B / "preds" / f"dev_future_unseen_fold{k}__{var}__h{h}.parquet") for k in range(4)], ignore_index=True)
        col = F["ae_seasonal_naive"].dropna()
        m["cells"][key] = {"variable": var, "h": h, "method": "yesterday", "anchor": None, "explain_validated": True,
                           "range": {"use": "plain", "plain": conformal_q(col.to_numpy(), 0.10), "day": 0.0, "night": 0.0},
                           "mae_method": float(col.mean()), "mae_simple": float(min(F["ae_persistence"].mean(), col.mean()))}
    m["bundle_version"] = "final_v2"
    m["derived_from"] = "final_v1"
    m["code_git_sha"] = git_sha
    m["changes_from_v1"] = ["Oxygen 6 h and temperature 6 h: trained model replaced by the plain guess 'same time yesterday' (pre-registered fallback; the models failed the sealed test against that guess).",
                            "Evidence text updated to the sealed final test. Ranges for the two switched cells are calibrated on validation errors of the plain guess and have NOT been re-tested."]
    m["evidence"] = ["We tested the final system once on 4 ponds it had never seen, over about 10 days later than anything it learned from. It was a locked test, run one time.",
                     "Oxygen 15 minutes ahead: the computer missed by about 0.33 mg/L; repeating the latest reading missed by 0.39. Oxygen 1 hour ahead: 0.71 against 1.12. Water temperature 1 hour ahead: 0.10 °C against 0.14. In these three cases the computer was clearly better than both plain guesses.",
                     "At 6 hours, the reading from the same time yesterday did as well as, or better than, the computer model (oxygen 1.52 against 1.66 mg/L; temperature 0.20 against 0.25 °C). So the app simply uses yesterday's reading there, and says so. pH, and temperature 15 minutes ahead, also use plain guesses because models did not clearly beat them.",
                     "The \"likely between\" ranges contained the real value 92% to 99% of the time in the final test. They were usually wider than needed, because the test days were calmer than the days they were calibrated on.",
                     "The chance of very low oxygen ranked risky moments better than three simple rules for the next 3 and 6 hours (not clearly for the next hour). But its percentages were often too high, and \"High chance\" appeared on almost every day, so use it only as a hint. It is experimental.",
                     "We tested the reasons shown for each answer for stability earlier: 9 of 11 passed; the oxygen 15-minute reasons are shown with a warning."]
    m["limits"] = m["limits"] + ["The final test covered about 10 days and 4 ponds in one region (late January). It says little about other seasons, places or longer periods."]
    write_manifest(BUNDLE2, m)
    artifact_vol.commit()
    return {"status": "written", "verified": verify_bundle(BUNDLE2), "files_removed": 6}


@app.local_entrypoint()
def build_v2_run(git_sha: str = "unknown", force: bool = False):
    print("V2:", json.dumps(build_v2.remote(git_sha, force)))
