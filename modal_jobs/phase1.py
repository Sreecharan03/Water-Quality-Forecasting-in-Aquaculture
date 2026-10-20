"""Phase 1 jobs: remote ingestion, profiling, and remote unit tests.

Run from the repo root (profile selected via MODAL_PROFILE):
    modal run -m modal_jobs.phase1
"""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import ARTIFACT_MOUNT, DATA_MOUNT, VOLUMES, app, artifact_vol, data_vol, image

CFG = Path("/root/configs/data_sources.yaml")


def _cfg() -> dict:
    import yaml
    return yaml.safe_load(CFG.read_text(encoding="utf-8"))


@app.function(image=image, volumes=VOLUMES, timeout=900)
def ingest(source_id: str = "fwi-data-campaign", force: bool = False) -> dict:
    from aquatic_xai.data.ingest import ingest_github
    data_vol.reload()
    manifest = ingest_github(source_id, _cfg()["sources"][source_id], Path(DATA_MOUNT), force=force)
    data_vol.commit()
    return {k: manifest[k] for k in ("commit_sha", "retrieved_utc", "n_files", "total_bytes")}


@app.function(image=image, volumes=VOLUMES, timeout=900, cpu=2.0)
def profile(source_id: str = "fwi-data-campaign", commit_sha: str = "") -> str:
    import pandas as pd
    from aquatic_xai.data.profile import profile_pond, to_markdown
    data_vol.reload()
    cfg = _cfg()
    src = cfg["sources"][source_id]
    manifest_path = next(Path(DATA_MOUNT, "manifests").glob(f"raw_{source_id}_{commit_sha or '*'}.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_dir = Path(DATA_MOUNT, "raw", source_id, manifest["commit_sha"])

    ponds = sorted(raw_dir.glob(src["pond_file_glob"]))
    per_pond = {p.stem: profile_pond(pd.read_csv(p), cfg["profiling"]) for p in ponds}
    md = to_markdown(manifest, per_pond, cfg["profiling"])

    out = Path(ARTIFACT_MOUNT, "reports", "phase1", manifest["commit_sha"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(per_pond, indent=2), encoding="utf-8")
    (out / "inventory.md").write_text(md, encoding="utf-8")

    # Small reference sheets (event log and QC legend) are documentation, shown verbatim.
    extras = ["", "## Reference sheets (verbatim)"]
    for rel in src["metadata_files"]:
        extras += ["", f"### {rel}", "```", (raw_dir / rel).read_text(encoding="utf-8", errors="replace"), "```"]
    artifact_vol.commit()
    return md + "\n".join(extras)


@app.function(image=image, volumes=VOLUMES, timeout=900)
def diagnostics(source_id: str = "fwi-data-campaign") -> str:
    """Targeted follow-ups to the inventory: duplicates, zeros by date, long gaps by date, grid fit."""
    import pandas as pd
    data_vol.reload()
    cfg = _cfg()
    src = cfg["sources"][source_id]
    manifest = json.loads(next(Path(DATA_MOUNT, "manifests").glob(f"raw_{source_id}_*.json")).read_text(encoding="utf-8"))
    raw_dir = Path(DATA_MOUNT, "raw", source_id, manifest["commit_sha"])
    inv = json.loads((Path(ARTIFACT_MOUNT, "reports", "phase1", manifest["commit_sha"], "inventory.json")).read_text())
    L = ["# Phase 1 diagnostics", ""]
    zero_dates: dict = {}
    gap_dates: dict = {}
    for p in sorted(raw_dir.glob(src["pond_file_glob"])):
        df = pd.read_csv(p)
        ts_col, do_col, ph_col, t_col = df.columns[0], df.columns[1], df.columns[2], df.columns[3]
        df["_ts"] = pd.to_datetime(df[ts_col], errors="coerce")
        g = inv[p.stem]["grid"]
        L.append(f"- {p.stem}: off-grid rows={g['n_off_grid_rows']}, grid collisions={g['n_collisions']}")
        dup = df[df["_ts"].duplicated(keep=False)]
        if len(dup):
            grp = dup.groupby("_ts")[[do_col, ph_col, t_col]].nunique(dropna=False)
            conflicting = int((grp.max(axis=1) > 1).sum())
            L.append(f"  - duplicate timestamps: {grp.shape[0]} groups, {conflicting} with CONFLICTING values, "
                     f"range {dup['_ts'].min()} .. {dup['_ts'].max()}")
            ex = dup.sort_values("_ts").head(4)[[ts_col, do_col, ph_col, t_col]]
            L.append("  - example rows: " + "; ".join(map(str, ex.values.tolist())))
        z = df[(df[do_col] == 0) | (df[ph_col] == 0) | (df[t_col] == 0)]
        for d, n in z["_ts"].dt.date.value_counts().items():
            zero_dates[str(d)] = zero_dates.get(str(d), 0) + int(n)
        s = df.dropna(subset=["_ts"]).drop_duplicates("_ts").sort_values("_ts")
        gaps = s["_ts"].diff().dt.total_seconds().div(60)
        for d in s.loc[gaps > 60, "_ts"].dt.date:
            gap_dates[str(d)] = gap_dates.get(str(d), 0) + 1
    L += ["", "## Rows with any zero, by date (all ponds)", ", ".join(f"{k}:{v}" for k, v in sorted(zero_dates.items())),
          "", "## Gaps >60 min ending on date (count of gaps, all ponds)",
          ", ".join(f"{k}:{v}" for k, v in sorted(gap_dates.items(), key=lambda x: -x[1])[:15])]
    return "\n".join(L)


@app.function(image=image, timeout=300)
def run_tests() -> str:
    import subprocess
    r = subprocess.run(["python", "-m", "pytest", "-q", "/root/tests", "-p", "no:cacheprovider"],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


@app.local_entrypoint()
def diag():
    print(run_tests.remote())
    print(diagnostics.remote())


@app.local_entrypoint()
def main(skip_tests: bool = False, force: bool = False):
    if not skip_tests:
        print(run_tests.remote())
    info = ingest.remote(force=force)
    print("INGEST:", json.dumps(info))
    print(profile.remote(commit_sha=info["commit_sha"]))
