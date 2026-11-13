"""Phase 3 jobs: causal feature tables, leakage tests on real tables, alignment examples.

Run from the repo root (profile selected via MODAL_PROFILE):
    modal run -m modal_jobs.phase3
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _latest_processed_version() -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob("processed_pp-*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))["dataset_version"]


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def build_features(dataset_version: str = "") -> dict:
    """Build write-once feature tables from the approved processed dataset."""
    import pandas as pd
    from aquatic_xai.data.clean import content_hash
    from aquatic_xai.features.build import FEATURE_CODE_VERSION, build_pond_table, feature_version
    data_vol.reload()
    rules, fcfg = _yaml("quality_rules.yaml"), _yaml("features.yaml")["features"]
    dv = dataset_version or _latest_processed_version()
    ver = feature_version(dv, fcfg)
    ddir = Path(DATA_MOUNT, "processed", dv)
    tables, hashes, stats = {}, {}, {}
    for f in sorted(ddir.glob("*.parquet")):
        t, grid, not_placed = build_pond_table(pd.read_parquet(f), rules, fcfg, f.stem)
        tables[f.stem] = t
        hashes[f.stem] = content_hash(t)
        stats[f.stem] = {"rows": int(len(t)), "grid_points": int(len(grid)), "rows_not_placed_on_grid": not_placed}
    out_dir = Path(DATA_MOUNT, "features", ver)
    mpath = Path(DATA_MOUNT, "manifests", f"features_{ver}.json")
    if mpath.exists():
        same = json.loads(mpath.read_text(encoding="utf-8"))["content_hashes"] == hashes
        return {"feature_version": ver, "dataset_version": dv, "status": "reproduced_identical" if same else "MISMATCH"}
    out_dir.mkdir(parents=True, exist_ok=True)
    for pond, t in tables.items():
        t.to_parquet(out_dir / f"{pond}.parquet", index=False)
    tmp = mpath.with_suffix(".json.part")
    tmp.write_text(json.dumps({"feature_version": ver, "code": FEATURE_CODE_VERSION, "dataset_version": dv,
                               "config": fcfg, "content_hashes": hashes, "stats": stats}, indent=2), encoding="utf-8")
    tmp.replace(mpath)
    data_vol.commit()
    return {"feature_version": ver, "dataset_version": dv, "status": "written", "ponds": len(tables),
            "rows": sum(s["rows"] for s in stats.values()), "n_features": len(next(iter(tables.values())).columns)}


@app.function(image=image, volumes=VOLUMES, timeout=3000, cpu=2.0)
def verify_and_report(feature_version: str, dataset_version: str) -> str:
    import numpy as np
    import pandas as pd
    from aquatic_xai.features.build import build_pond_table
    from aquatic_xai.features.dictionary import feature_specs, to_markdown
    from aquatic_xai.features.leakage import identity_check, prefix_invariance, sample_origins, target_alignment
    data_vol.reload()
    rules, allcfg = _yaml("quality_rules.yaml"), _yaml("features.yaml")
    fcfg, lcfg, icfg = allcfg["features"], allcfg["leakage_tests"], allcfg["informativeness"]
    nominal, tol = rules["grid"]["nominal_interval_min"], rules["grid"]["grid_tolerance_min"]
    fdir, ddir = Path(DATA_MOUNT, "features", feature_version), Path(DATA_MOUNT, "processed", dataset_version)
    tables = {f.stem: pd.read_parquet(f) for f in sorted(fdir.glob("*.parquet"))}

    specs = feature_specs(fcfg)
    spec_names = {s["name"] for s in specs}
    sample_tbl = next(iter(tables.values()))
    built = {c for c in sample_tbl.columns if not c.startswith(("y_", "ts_target", "pond", "grid_idx", "ts_ist", "is_warmup"))}
    dict_ok = spec_names == built

    # --- leakage tests on the stored real tables
    pi_tot = {"origins_checked": 0, "mismatching_origins": 0, "max_abs_diff": 0.0}
    ta_tot = {"target_values_checked": 0, "mismatches": 0}
    for pond, t in tables.items():
        proc = pd.read_parquet(ddir / f"{pond}.parquet")
        _, grid, _ = build_pond_table(proc, rules, fcfg, pond)
        rows = sample_origins(t, lcfg["samples_per_pond"], lcfg["seed"])
        pi = prefix_invariance(grid, t, fcfg, rows, nominal)
        ta = target_alignment(proc, t, fcfg, rows, nominal, tol)
        pi_tot["origins_checked"] += pi["origins_checked"]
        pi_tot["mismatching_origins"] += pi["mismatching_origins"]
        pi_tot["max_abs_diff"] = max(pi_tot["max_abs_diff"], pi["max_abs_diff"])
        ta_tot["target_values_checked"] += ta["target_values_checked"]
        ta_tot["mismatches"] += ta["mismatches"]
    ident = identity_check(pd.concat(tables.values(), ignore_index=True), fcfg)

    # --- coverage
    allt = pd.concat(tables.values(), ignore_index=True)
    use = allt[~allt["is_warmup"]]
    cov = []
    for v in fcfg["variables"]:
        for h in fcfg["horizons"]:
            y = use[f"y_{v}_h{h}"].notna()
            both = y & use[f"{v}_cur"].notna()
            good = both & (use[f"{v}_valid_frac24"] >= 0.8)
            cov.append(f"| {v} | {h * nominal} min | {int(y.sum())} | {int(both.sum())} | {int(good.sum())} |")
    nan_rate = allt[sorted(built)].isna().mean().sort_values(ascending=False).head(8)

    # --- alignment examples (independent raw lookup)
    ex = ["| pond | horizon | origin (IST) | DO_cur | DO_lag4 (raw value 60 min earlier) | target time | y_DO | raw DO at target time |", "|---|---|---|---|---|---|---|---|"]
    for pond in ("ara2_573a2826", "ara2_3b2f3973", "ara2_ca187575"):
        t, proc = tables[pond], pd.read_parquet(ddir / f"{pond}.parquet")
        pidx = proc.set_index("ts_ist")["DO"]
        for h in fcfg["horizons"]:
            c = t[(~t["is_warmup"]) & t["DO_cur"].notna() & t["DO_lag4"].notna() & t[f"y_DO_h{h}"].notna()]
            r = c.iloc[len(c) // 2]
            tgt_t, org = r[f"ts_target_h{h}"], r["ts_ist"]
            raw_tgt = pidx.reindex(pidx.index[(pidx.index >= tgt_t - pd.Timedelta(minutes=tol)) & (pidx.index <= tgt_t + pd.Timedelta(minutes=tol))])
            raw_lag = pidx[(pidx.index >= org - pd.Timedelta(minutes=60 + tol)) & (pidx.index <= org - pd.Timedelta(minutes=60 - tol))]
            ex.append(f"| {pond} | {h * nominal} min | {org} | {r['DO_cur']:.2f} | {r['DO_lag4']:.2f} ({', '.join(f'{x:.2f}' for x in raw_lag.dropna().head(2))}) | "
                      f"{tgt_t} | {r[f'y_DO_h{h}']:.2f} | {', '.join(f'{x:.2f}' for x in raw_tgt.dropna().head(2))} |")

    # --- descriptive source informativeness on the first 50% of each pond's timeline (not used for selection)
    parts = []
    for t in tables.values():
        cut = t["ts_ist"].min() + (t["ts_ist"].max() - t["ts_ist"].min()) * icfg["train_like_fraction"]
        parts.append(t[(t["ts_ist"] <= cut) & ~t["is_warmup"]])
    early = pd.concat(parts, ignore_index=True)
    group_of = {s["name"]: s["group"] for s in specs}
    info = []
    for v in fcfg["variables"]:
        for h in icfg["horizons"]:
            rho = early[sorted(built)].corrwith(early[f"y_{v}_h{h}"], method="spearman").abs().dropna()
            best_by_group = {g: (max((n for n in rho.index if group_of[n] == g), key=lambda n: rho[n]) if any(group_of[n] == g for n in rho.index) else None) for g in ("history", "rolling", "quality", "time")}
            top = ", ".join(f"{n} ({rho[n]:.2f})" for n in rho.sort_values(ascending=False).head(icfg["top_k"]).index)
            grp = "; ".join(f"{g}: {n} ({rho[n]:.2f})" for g, n in best_by_group.items() if n)
            info.append(f"| {v} | {h * nominal} min | {top} | {grp} |")

    md_dict = to_markdown(specs, fcfg, feature_version)
    out = Path(ARTIFACT_MOUNT, "reports", "phase3", feature_version)
    out.mkdir(parents=True, exist_ok=True)
    (out / "feature_dictionary.md").write_text(md_dict, encoding="utf-8")

    L = [f"# Phase 3 feature report, `{feature_version}` (from dataset `{dataset_version}`)", "",
         f"- Feature table: {len(allt)} origins, {len(built)} features, {len([c for c in allt.columns if c.startswith('y_')])} targets, {len(tables)} ponds",
         f"- Warm-up origins (history < 6 h, kept but flagged `is_warmup`): {int(allt['is_warmup'].sum())}",
         f"- Dictionary matches built columns exactly: **{dict_ok}**", "",
         "## Leakage and alignment tests on the real tables", "",
         f"- Prefix invariance (features recomputed after cutting off all future data): {pi_tot['origins_checked']} origins, "
         f"**{pi_tot['mismatching_origins']} mismatches**, max abs diff {pi_tot['max_abs_diff']:.2e}",
         f"- Target alignment (independent timestamp lookup): {ta_tot['target_values_checked']} target values checked, **{ta_tot['mismatches']} mismatches**",
         f"- Feature==target identity: max equal fraction {ident['max_equal_fraction']} ({ident['feature']} vs {ident['target']})", "",
         "## Coverage (non-warm-up origins)", "",
         "| target | horizon | origins with valid target | + valid current reading | + >=80% valid in last 6 h |", "|---|---|---|---|---|", *cov, "",
         "Highest missing-value rates among features (fraction NaN): " + ", ".join(f"{k}={v:.3f}" for k, v in nan_rate.items()), "",
         "## Temporal alignment examples (DO; origin to target, with raw lookups)", "", *ex, "",
         "## Descriptive source informativeness (|Spearman|, first 50% of each pond's timeline, no model; NOT used for selection)", "",
         "| target | horizon | top features overall | best feature per group |", "|---|---|---|---|", *info]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md + "\n\n@@DICTIONARY@@\n" + md_dict


@app.function(image=image, timeout=300)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


@app.local_entrypoint()
def main():
    print(tests_remote.remote())
    first = build_features.remote()
    print("BUILD #1:", json.dumps(first))
    second = build_features.remote()
    print("BUILD #2 (idempotence check):", json.dumps(second))
    if second["status"] != "reproduced_identical":
        raise SystemExit("Idempotence check FAILED")
    text = verify_and_report.remote(first["feature_version"], first["dataset_version"])
    report, dictionary = text.split("\n\n@@DICTIONARY@@\n")
    Path("docs").mkdir(exist_ok=True)
    Path("docs/feature_dictionary.md").write_text(dictionary, encoding="utf-8")   # metadata only, no data
    print(report)
