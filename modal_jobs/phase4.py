"""Phase 4 jobs: temporal + unseen-pond split design.

Run from the repo root (profile selected via MODAL_PROFILE):
    modal run -m modal_jobs.phase4::calendar     # read-only look at origins per day
    modal run -m modal_jobs.phase4               # build, verify, report (added below)
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _latest_feature_version() -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob("features_ft-*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))["feature_version"]


@app.function(image=image, volumes=VOLUMES, timeout=600)
def calendar_view(feature_version: str = "") -> str:
    """Origins per calendar day and per pond (aggregates only), to choose split cutoffs sensibly."""
    import pandas as pd
    data_vol.reload()
    fv = feature_version or _latest_feature_version()
    cols = ["pond", "ts_ist", "is_warmup", "y_DO_h24", "y_pH_h24", "y_Temp_h24"]
    d = pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(Path(DATA_MOUNT, "features", fv).glob("*.parquet"))])
    d = d[~d["is_warmup"]]
    d["ok"] = d[["y_DO_h24", "y_pH_h24", "y_Temp_h24"]].notna().all(axis=1)
    d["day"] = d["ts_ist"].dt.date
    per_day = d.groupby("day").agg(origins=("ok", "size"), usable=("ok", "sum"), ponds=("pond", "nunique"))
    per_day["cum_share"] = (per_day["usable"].cumsum() / per_day["usable"].sum()).round(3)
    per_pond = d.groupby("pond").agg(first=("ts_ist", "min"), last=("ts_ist", "max"), usable=("ok", "sum"))
    return f"feature version {fv}\n\n{per_day.to_string()}\n\n{per_pond.to_string()}"


def _load_tables(fv: str):
    import pandas as pd
    cols = ["pond", "grid_idx", "ts_ist", "is_warmup", "ts_target_h24"] + \
           [f"y_{v}_h{h}" for v in ("DO", "pH", "Temp") for h in (1, 4, 24)]
    return pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(Path(DATA_MOUNT, "features", fv).glob("*.parquet"))],
                     ignore_index=True)


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def build_splits(feature_version: str = "") -> dict:
    """Write-once split assignments. If the version exists, verify the rebuild is identical."""
    from aquatic_xai.splits.manifest import (SPLIT_CODE_VERSION, build_assignments, check_assignments, content_hash,
                                             split_version)
    data_vol.reload()
    cfg = _yaml("splits.yaml")["splits"]
    fv = feature_version or _latest_feature_version()
    ver = split_version(fv, cfg)
    table = _load_tables(fv)
    a, info = build_assignments(table, cfg)
    chk = check_assignments(a, info, cfg)
    h = content_hash(a)
    mpath = Path(DATA_MOUNT, "manifests", f"splits_{ver}.json")
    if mpath.exists():
        same = json.loads(mpath.read_text(encoding="utf-8"))["assignments_content_hash"] == h
        return {"split_version": ver, "feature_version": fv, "status": "reproduced_identical" if same else "MISMATCH"}
    if not chk["all_pass"]:
        return {"split_version": ver, "feature_version": fv, "status": "CHECKS_FAILED", "checks": chk}
    out = Path(DATA_MOUNT, "splits", ver)
    out.mkdir(parents=True, exist_ok=True)
    a.to_parquet(out / "assignments.parquet", index=False)
    tmp = mpath.with_suffix(".json.part")
    tmp.write_text(json.dumps({"split_version": ver, "code": SPLIT_CODE_VERSION, "feature_version": fv, "config": cfg,
                               "assignments_content_hash": h, "info": info, "checks": chk}, indent=2), encoding="utf-8")
    tmp.replace(mpath)
    data_vol.commit()
    return {"split_version": ver, "feature_version": fv, "status": "written", "rows": int(len(a))}


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def split_report(split_version: str) -> str:
    import pandas as pd
    from aquatic_xai.reports.figures import plot_split
    from aquatic_xai.splits.manifest import gantt_text, regimes, role_counts
    data_vol.reload()
    man = json.loads(Path(DATA_MOUNT, "manifests", f"splits_{split_version}.json").read_text(encoding="utf-8"))
    cfg, info, chk = man["config"], man["info"], man["checks"]
    a = pd.read_parquet(Path(DATA_MOUNT, "splits", split_version, "assignments.parquet"))
    table = _load_tables(man["feature_version"])
    rc = role_counts(a, table)

    out = Path(ARTIFACT_MOUNT, "reports", "phase4", split_version)
    out.mkdir(parents=True, exist_ok=True)
    plot_split(a, info, out / "split_design.png")

    # per-pond summary
    rows = []
    for p in sorted(a["pond"].unique()):
        g = a[(a["pond"] == p) & ~a["is_warmup"]]
        u = lambda r: int(((g["role"] == r) & table.loc[g.index, "y_DO_h24"].notna()).sum())
        rows.append(f"| {p} | {'SEALED' if p in info['sealed_ponds'] else 'dev'} | {info['folds'].get(p, 'n/a')} | "
                    f"{u('dev_train')} | {u('dev_val')} | {u('seen_pond_test')} | {u('unseen_pond_test')} |")
    L = [f"# Phase 4 split report, `{split_version}` (features `{man['feature_version']}`)", "",
         f"- Calendar cutoffs (IST): train ends **{info['cutoff_train_end']}**, validation ends **{info['cutoff_val_end']}**; "
         f"embargo {info['embargo_hours']} h (>= 6 h lookback + 6 h horizon)",
         f"- Sealed unseen-pond test ponds (seed {info['seed']}, drawn from {len(info['eligible_sealed_ponds'])} eligible): {info['sealed_ponds']}",
         f"- Development ponds ({len(info['dev_ponds'])}) in {cfg['cv_folds']} grouped folds; fold -1 = never held out",
         f"- Assignment content hash: `{man['assignments_content_hash']}`", "",
         "## Independence checks (all must pass)", "",
         f"- Unique (pond, origin) rows: **{chk['unique_rows']}** ({chk['row_accounting']} rows)",
         f"- Gap between last train target and first val feature window: **{chk['gap_hours_train_to_val']:.2f} h**; val to test: "
         f"**{chk['gap_hours_val_to_test']:.2f} h**; train to test: **{chk['gap_hours_train_to_test']:.2f} h** (must be >= 0): embargo_ok = **{chk['embargo_ok']}**",
         f"- Sealed-pond rows appearing in any development role: **{chk['sealed_rows_in_dev_roles']}**; sealed ponds disjoint from dev ponds: **{chk['sealed_ponds_disjoint_from_dev']}**",
         f"- All {len(chk['regimes'])} evaluation regimes pass (no row overlap, no pond overlap for unseen regimes, evaluation strictly in the future): **{chk['all_regimes_pass']}**", "",
         "| regime | kind | train rows | eval rows | eval ponds | row overlap | pond overlap | gap h | pass |", "|---|---|---|---|---|---|---|---|---|"]
    for r in chk["regimes"]:
        gh = "n/a" if r["gap_hours"] is None else f"{r['gap_hours']:.2f}"
        L.append(f"| {r['regime']} | {r['kind']} | {r['train_rows']} | {r['eval_rows']} | {r['eval_ponds']} | {r['row_overlap']} | {len(r['pond_overlap'])} | {gh} | {r['pass']} |")
    L += ["", "## Origins by role (DO targets with a valid value)", "",
          "| role | origins | ponds | DO 15 min | DO 1 h | DO 6 h |", "|---|---|---|---|---|---|"]
    for role, r in rc.iterrows():
        L.append(f"| {role} | {r['origins']} | {r['ponds']} | {r['DO_h1_valid_target']} | {r['DO_h4_valid_target']} | {r['DO_h24_valid_target']} |")
    L += ["", "## Per pond (origins with a valid 6 h DO target)", "",
          "| pond | status | fold | train | val | seen-pond test | unseen-pond test |", "|---|---|---|---|---|---|---|", *rows, "",
          "## Chronological and pond split (one character per day)", "",
          "T train, V validation, X seen-pond test (sealed), S unseen-pond test (sealed), o sealed pond data kept unused, . no data", "",
          "```", gantt_text(a, info), "```", "",
          f"Chart: `/artifacts/reports/phase4/{split_version}/split_design.png` (volume `aquatic-xai-artifacts`)"]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md + "\n\n@@MANIFEST@@\n" + json.dumps({"split_version": split_version, "feature_version": man["feature_version"],
                                                  "config": cfg, "assignments_content_hash": man["assignments_content_hash"],
                                                  "info": info, "regimes": [r["regime"] for r in chk["regimes"]]}, indent=2)


@app.function(image=image, timeout=300)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


@app.local_entrypoint()
def calendar():
    print(calendar_view.remote())


@app.local_entrypoint()
def main():
    print(tests_remote.remote())
    first = build_splits.remote()
    print("BUILD #1:", json.dumps(first))
    if first["status"] not in ("written", "reproduced_identical"):
        raise SystemExit("split build did not succeed")
    second = build_splits.remote()
    print("BUILD #2 (idempotence check):", json.dumps(second))
    if second["status"] != "reproduced_identical":
        raise SystemExit("Idempotence check FAILED")
    text = split_report.remote(first["split_version"])
    report, manifest = text.split("\n\n@@MANIFEST@@\n")
    Path("docs/splits").mkdir(parents=True, exist_ok=True)
    Path("docs/splits/split_manifest.json").write_text(manifest, encoding="utf-8")   # pond roles and counts only, no sensor data
    print(report)
