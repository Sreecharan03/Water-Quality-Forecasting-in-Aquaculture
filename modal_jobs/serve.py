"""Public web deployment of the app on Modal. NOT deployed by default: deploying makes the page reachable by anyone with the link,
so it needs an explicit decision (see docs/app_runbook.md).

    modal serve  -m modal_jobs.serve      # temporary URL while the command runs (for a demo or a check)
    modal deploy -m modal_jobs.serve      # permanent URL (outward-facing: only after approval)
"""
from __future__ import annotations

from modal_jobs.common import ARTIFACT_MOUNT, VOLUMES, app, image

import modal


@app.function(image=image, volumes=VOLUMES, min_containers=0, scaledown_window=300, timeout=120)
@modal.asgi_app()
def web():
    from app.main import create_app
    return create_app(f"{ARTIFACT_MOUNT}/models/final_v1")
