"""Phase 2 jobs: quality-aware preprocessing, idempotence check, treatment comparison.

Run from the repo root (profile selected via MODAL_PROFILE):
    modal run -m modal_jobs.phase2
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image

SOURCE_ID = "fwi-data-campaign"


def _yaml(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def _raw_manifest(commit_sha: str = "") -> dict:
    path = next(Path(DATA_MOUNT, "manifests").glob(f"raw_{SOURCE_ID}_{commit_sha or '*'}.json"))
    return json.loads(path.read_text(encoding="utf-8"))


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def preprocess() -> dict:
    """Clean all pond files. Write-once: if the dataset version exists, verify it reproduces identically."""
    import pandas as pd
    from aquatic_xai.data.clean import CLEAN_VERSION, clean_pond, content_hash, dataset_version
    data_vol.reload()
    rules = _yaml("quality_rules.yaml")
    src = _yaml("data_sources.yaml")["sources"][SOURCE_ID]
    manifest = _raw_manifest()
    version = dataset_version(manifest["commit_sha"], rules)
    raw_dir = Path(DATA_MOUNT, "raw", SOURCE_ID, manifest["commit_sha"])

    results, hashes, counts = {}, {}, {}
    for f in sorted(raw_dir.glob(src["pond_file_glob"])):
        proc, quar, cnt = clean_pond(pd.read_csv(f), rules)
        results[f.stem] = (proc, quar)
        hashes[f.stem] = {"processed": content_hash(proc), "quarantine": content_hash(quar)}
        counts[f.stem] = cnt

    out_dir = Path(DATA_MOUNT, "processed", version)
    mpath = Path(DATA_MOUNT, "manifests", f"processed_{version}.json")
    if mpath.exists():
        old = json.loads(mpath.read_text(encoding="utf-8"))
        same = old["content_hashes"] == hashes
        return {"version": version, "status": "reproduced_identical" if same else "MISMATCH", "ponds": len(hashes)}

    (out_dir / "_quarantine").mkdir(parents=True, exist_ok=True)
    for pond, (proc, quar) in results.items():
        proc.to_parquet(out_dir / f"{pond}.parquet", index=False)
        quar.to_parquet(out_dir / "_quarantine" / f"{pond}.parquet", index=False)
    tmp = mpath.with_suffix(".json.part")
    tmp.write_text(json.dumps({
        "dataset_version": version, "clean_version": CLEAN_VERSION, "raw_commit_sha": manifest["commit_sha"],
        "rules": rules, "content_hashes": hashes, "counts": counts}, indent=2), encoding="utf-8")
    tmp.replace(mpath)
    data_vol.commit()
    totals = {k: sum(c[k] for c in counts.values()) for k in ("n_raw_rows", "n_processed_rows", "n_quarantined_rows")}
    return {"version": version, "status": "written", "ponds": len(hashes), **totals}


@app.function(image=image, volumes=VOLUMES, timeout=1800, cpu=2.0)
def analyze(version: str) -> str:
    import pandas as pd
    from aquatic_xai.data.treatments import (calibration_shift, compare_treatments, examples_by_category,
                                             missingness_profile)
    from aquatic_xai.reports.figures import plot_cleaning_audit
    data_vol.reload()
    rules = _yaml("quality_rules.yaml")
    ddir = Path(DATA_MOUNT, "processed", version)
    proc = {f.stem: pd.read_parquet(f) for f in sorted(ddir.glob("*.parquet"))}
    manifest = json.loads(Path(DATA_MOUNT, "manifests", f"processed_{version}.json").read_text(encoding="utf-8"))

    rows = compare_treatments(proc, rules)
    cal = calibration_shift(proc, rules["calibration_check"])
    miss = missingness_profile(proc, rules)
    ex = examples_by_category(proc)

    out = Path(ARTIFACT_MOUNT, "reports", "phase2", version)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    plot_cleaning_audit(proc, ["ara2_3ed4df8e", "ara2_ca187575", "ara2_3b2f3973"], out / "plots" / "cleaning_audit.png",
                        rules["calibration_check"]["event_date"])
    (out / "treatments.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "calibration.json").write_text(json.dumps(cal, indent=2), encoding="utf-8")
    (out / "missingness.json").write_text(json.dumps(miss, indent=2), encoding="utf-8")

    c = manifest["counts"]
    tot = {k: sum(x[k] for x in c.values()) for k in ("n_raw_rows", "n_processed_rows", "n_quarantined_rows")}
    status_tot = {v: {} for v in ("DO", "pH", "Temp")}
    for x in c.values():
        for v, d in x["status"].items():
            for k, n in d.items():
                status_tot[v][k] = status_tot[v].get(k, 0) + n

    L = [f"# Phase 2 preprocessing report, dataset `{version}`", "",
         f"- Raw commit: `{manifest['raw_commit_sha']}` | code: {manifest['clean_version']}",
         f"- Rows: raw {tot['n_raw_rows']} = processed {tot['n_processed_rows']} + quarantined {tot['n_quarantined_rows']} "
         f"(accounting check passed for every pond)", "",
         "## Cell status after cleaning (all ponds)", "", "| variable | " + " | ".join(sorted({k for d in status_tot.values() for k in d})) + " |",
         "|---|" + "---|" * len({k for d in status_tot.values() for k in d})]
    keys = sorted({k for d in status_tot.values() for k in d})
    for v, d in status_tot.items():
        L.append(f"| {v} | " + " | ".join(str(d.get(k, 0)) for k in keys) + " |")
    L += ["", "## Treatment comparison (pooled over 17 ponds)", "",
          "| treatment | valid DO | valid pH | valid Temp | DO median | DO p01 | DO p99 | DO<1.0 kept | DO<0.1 kept | "
          + " | ".join(k.replace("origins_", "origins ") for k in rows[0] if k.startswith("origins_")) + " |",
          "|---|" + "---|" * (8 + len([k for k in rows[0] if k.startswith("origins_")]))]
    for r in rows:
        L.append(f"| {r['treatment']} | {r['n_valid_DO']} | {r['n_valid_pH']} | {r['n_valid_Temp']} | {r['DO_median']:.2f} | "
                 f"{r['DO_p01']:.2f} | {r['DO_p99']:.2f} | {r['n_DO_below_critical']} | {r['n_DO_below_near_zero']} | "
                 + " | ".join(str(r[k]) for k in r if k.startswith("origins_")) + " |")
    L += ["", "## Missingness (grid points with no row), by IST time of day", "",
          json.dumps(miss["missing_fraction_by_4h_block_IST"]), "", "Cell counts by cause:", "", "```", json.dumps(miss["cells"], indent=1), "```",
          "", f"## Calibration event {rules['calibration_check']['event_date']}: median shift vs typical 3-day shifts", "",
          "Percentile = share of ordinary 5-day-apart window shifts in the same pond that are smaller than the shift across the event.", "",
          json.dumps(cal["summary"], indent=1), "", "Per pond/variable shifts with percentile >= 0.9:", ""]
    L += [f"- {r['pond']} {r['var']}: delta_median={r['delta_median']}, percentile={r['percentile_vs_typical']}"
          for r in cal["per_pond"] if r["percentile_vs_typical"] >= 0.9]
    L += ["", "## Manual-review examples (first rows per category)", ""]
    for k, v in ex.items():
        L += [f"- **{k}**:"] + [f"  - {e}" for e in v]
    L += ["", f"Plot: `/artifacts/reports/phase2/{version}/plots/cleaning_audit.png` (Modal volume `aquatic-xai-artifacts`)"]
    md = "\n".join(L)
    (out / "report.md").write_text(md, encoding="utf-8")
    artifact_vol.commit()
    return md


@app.function(image=image, volumes=VOLUMES, timeout=600)
def temp_step_check(version: str, start: str = "2026-01-05", end: str = "2026-01-12") -> str:
    """Is the Jan-8 temperature drop abrupt (calibration-like) or gradual (weather-like)?
    Cross-pond median of valid Temp per 6-hour bin; aggregates only."""
    import pandas as pd
    data_vol.reload()
    ddir = Path(DATA_MOUNT, "processed", version)
    frames = []
    for f in sorted(ddir.glob("*.parquet")):
        p = pd.read_parquet(f, columns=["ts_ist", "Temp", "DO", "pH"]).dropna(subset=["Temp"])
        p["pond"] = f.stem
        frames.append(p)
    d = pd.concat(frames)
    d = d[(d["ts_ist"] >= start) & (d["ts_ist"] < end)]
    d["bin"] = d["ts_ist"].dt.floor("6h")
    per_pond = d.groupby(["bin", "pond"])["Temp"].median().reset_index()
    agg = per_pond.groupby("bin")["Temp"].agg(["median", "min", "max", "count"]).round(2)
    # same-hour comparison removes the diurnal cycle: daily mean of the 4 bins per pond
    d["day"] = d["ts_ist"].dt.floor("1D")
    daily = d.groupby(["day", "pond"])["Temp"].mean().reset_index().groupby("day")["Temp"].agg(["median", "count"]).round(2)
    return "6-hour cross-pond Temp (median of pond medians, min, max, n ponds):\n" + agg.to_string() + \
           "\n\nDaily mean Temp (median across ponds):\n" + daily.to_string()


@app.function(image=image, timeout=300)
def tests_remote() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


@app.local_entrypoint()
def tempcheck(version: str = "pp-682986049e51"):
    print(temp_step_check.remote(version))


@app.local_entrypoint()
def main():
    print(tests_remote.remote())
    first = preprocess.remote()
    print("PREPROCESS #1:", json.dumps(first))
    second = preprocess.remote()
    print("PREPROCESS #2 (idempotence check):", json.dumps(second))
    if second["status"] != "reproduced_identical":
        raise SystemExit("Idempotence check FAILED")
    print(analyze.remote(first["version"]))
