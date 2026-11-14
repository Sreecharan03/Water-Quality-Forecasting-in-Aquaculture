"""Pond Water Forecast: FastAPI service + plain HTML/CSS/JS front end.

Run (after downloading the model bundle, see README):
    set AQUATIC_BUNDLE=bundle
    uvicorn app.main:app --port 8000
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from aquatic_xai.serving import ingest, plain

log = logging.getLogger("pond-forecast")
STATIC = Path(__file__).parent / "static"
HIDDEN_PREFIXES = ("_", "stuck_", "sparse_")


class Reading(BaseModel):
    time: str = Field(max_length=40)
    oxygen: str | float | None = None
    ph: str | float | None = None
    temperature: str | float | None = None


class ForecastRequest(BaseModel):
    pond_name: str = Field(default="My pond", max_length=60)
    csv_text: str | None = Field(default=None, max_length=2_000_000)
    rows: list[Reading] | None = Field(default=None, max_length=ingest.MAX_ROWS)


def create_app(bundle_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Pond Water Forecast", version="1.0", docs_url=None, redoc_url=None, openapi_url=None)
    state: dict = {"engine": None, "dir": bundle_dir or os.environ.get("AQUATIC_BUNDLE", "bundle")}

    def engine():
        if state["engine"] is None:
            from aquatic_xai.serving.engine import Engine
            state["engine"] = Engine(state["dir"])
        return state["engine"]

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "public, max-age=300"
        return resp

    @app.get("/api/health")
    def health():
        try:
            return {"status": "ok", "model_version": engine().version}
        except Exception:                                   # noqa: BLE001
            log.exception("bundle failed to load")
            return JSONResponse({"status": "unavailable"}, status_code=503)

    @app.get("/api/example")
    def example():
        return {"csv": ingest.example_csv(), "note": "Made-up numbers for a demonstration pond. These are not real measurements."}

    @app.get("/api/template", response_class=PlainTextResponse)
    def template():
        return PlainTextResponse(ingest.template_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pond_readings_template.csv"})

    @app.get("/api/about")
    def about():
        m = engine().m
        return {"model_version": m["bundle_version"], "built": m.get("created"), "evidence": m.get("evidence", []), "limits": m.get("limits", []), "disclaimer": plain.DISCLAIMER}

    @app.post("/api/forecast")
    def forecast(req: ForecastRequest):
        try:
            if req.csv_text:
                df = ingest.parse_text(req.csv_text)
            elif req.rows:
                df = ingest.rename_columns(pd.DataFrame([{"time": r.time, "oxygen": r.oxygen, "pH": r.ph, "temperature": r.temperature} for r in req.rows]))
            else:
                raise ingest.InputProblem("We did not receive any readings. Paste your readings or upload a file.")
            grid, issues, summary = ingest.prepare(df)
            result = engine().predict(grid, summary)
        except ingest.InputProblem as e:
            return JSONResponse({"problem": str(e)}, status_code=422)
        except Exception:                                   # noqa: BLE001
            log.exception("forecast failed")               # no readings are logged
            return JSONResponse({"problem": "Something went wrong on our side. Please try again, or check that your file has columns: time, oxygen, pH, temperature."}, status_code=500)
        issues = issues + [{"level": "warn", "text": w} for w in result.get("warnings", [])]
        shown = {k: v for k, v in summary.items() if not k.startswith(HIDDEN_PREFIXES)}
        tail = grid.tail(96)
        history = {v: [None if pd.isna(x) else round(float(x), 3) for x in tail[v]] for v in ("DO", "pH", "Temp")}
        return {"pond_name": req.pond_name.strip() or "My pond", "summary": shown, "issues": issues, "result": result, "history": history, "disclaimer": plain.DISCLAIMER}

    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


app = create_app()
