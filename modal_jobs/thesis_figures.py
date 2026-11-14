"""Build the thesis figures on Modal (aggregates only; nothing from the data volumes is read).

    modal run -m modal_jobs.thesis_figures::run --out docs/thesis/figures
"""
from __future__ import annotations

from pathlib import Path

from modal_jobs.common import app, image


@app.function(image=image, timeout=300)
def build() -> dict:
    from aquatic_xai.reports.thesis_figures import all_figures
    return all_figures()


@app.local_entrypoint()
def run(out: str = "docs/thesis/figures"):
    Path(out).mkdir(parents=True, exist_ok=True)
    for name, blob in build.remote().items():
        (Path(out) / name).write_bytes(blob)
        print("wrote", name, len(blob))
