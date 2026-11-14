"""Model bundle: LightGBM boosters + manifest. Shared by the Modal builder and the tests (which build a tiny synthetic bundle)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from aquatic_xai.features.daily import daily_specs
from aquatic_xai.features.dictionary import feature_specs
from aquatic_xai.models.anchored import anchored_columns
from aquatic_xai.models.tabular import feature_columns

# Per-cell plan, from the pre-registered recommendations (Phase 5b, Phase 6): model where it beat both simple guesses, else the best simple guess.
PLAN = {("DO", 1): ("model", "persistence"), ("DO", 4): ("model", "persistence"), ("DO", 24): ("model", "yesterday"),
        ("pH", 1): ("same_as_now", None), ("pH", 4): ("same_as_now", None), ("pH", 24): ("yesterday", None),
        ("Temp", 1): ("same_as_now", None), ("Temp", 4): ("model", "persistence"), ("Temp", 24): ("model", "yesterday")}
DAYNIGHT_CELLS = {("DO", 4), ("DO", 24), ("Temp", 4), ("Temp", 24)}          # Phase 6: plain ranges under-covered by day here
ALERT_WINDOWS = {4: "1h", 12: "3h", 24: "6h"}
EXPLAIN_VALIDATED = {("DO", 1): False}                                       # Phase 8: every other explained cell was validated


def model_columns(fcfg: dict, var: str, h: int, anchor: str) -> list[str]:
    cols = anchored_columns(feature_specs(fcfg), daily_specs(fcfg["horizons"]), var, h, False, anchor)
    return cols


def alert_columns(fcfg: dict, W: int) -> list[str]:
    return feature_columns(feature_specs(fcfg), False) + [s["name"] for s in daily_specs(fcfg["horizons"])] + [f"ydaymin_W{W}"]


def save_booster(model, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(path))


def sha256_dir(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            out[str(p.relative_to(root)).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def write_manifest(root: Path, manifest: dict) -> None:
    manifest = {**manifest, "files_sha256": sha256_dir(root)}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def verify_bundle(root: Path) -> bool:
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return m["files_sha256"] == sha256_dir(root)


def make_fake_bundle(root: Path, fcfg: dict, seed: int = 0) -> None:
    """Tiny synthetic bundle (random boosters) so the API and the engine can be tested without the real models."""
    import lightgbm as lgb
    rng = np.random.RandomState(seed)
    cells, alerts = {}, {}
    for (var, h), (method, anchor) in PLAN.items():
        cell = {"variable": var, "h": h, "method": method, "anchor": anchor, "range": {"use": "daynight" if (var, h) in DAYNIGHT_CELLS else "plain", "plain": 1.0, "day": 1.2, "night": 0.8},
                "explain_validated": EXPLAIN_VALIDATED.get((var, h), True), "mae_method": 0.5, "mae_simple": 0.7}
        if method == "model":
            cols = model_columns(fcfg, var, h, anchor)
            n = len(cols) + (1 if anchor == "yesterday" else 0)
            files = []
            for s in (0, 1):
                m = lgb.LGBMRegressor(n_estimators=8, num_leaves=4, min_child_samples=5, verbose=-1, random_state=s).fit(rng.normal(size=(200, n)), rng.normal(size=200))
                f = f"{var}_{h}_s{s}.txt"
                save_booster(m, root / "models" / f)
                files.append(f)
            cell.update({"columns": cols, "files": files})
        cells[f"{var}_{h}"] = cell
    for W, name in ALERT_WINDOWS.items():
        cols = alert_columns(fcfg, W)
        files = []
        for s in (0, 1):
            m = lgb.LGBMClassifier(n_estimators=8, num_leaves=4, min_child_samples=5, verbose=-1, random_state=s).fit(rng.normal(size=(200, len(cols))), rng.binomial(1, 0.4, 200))
            f = f"A_{W}_s{s}.txt"
            save_booster(m, root / "models" / f)
            files.append(f)
        alerts[str(W)] = {"columns": cols, "files": files, "calib": {"x": [0.0, 0.5, 1.0], "y": [0.0, 0.5, 1.0]}, "high_cal": 0.5, "explain_validated": True}
    write_manifest(root, {"bundle_version": "test-bundle", "created": "test", "features_cfg": fcfg, "day_steps": 96, "day_hours": [6, 18], "alert_threshold_mg_l": 2.0,
                          "cells": cells, "alerts": alerts, "evidence": ["Test bundle."], "limits": ["Test bundle."],
                          "training_range": {"DO": {"min": 0.01, "max": 24.0, "p1": 0.2, "p99": 20.0}, "pH": {"min": 5.3, "max": 9.2, "p1": 7.0, "p99": 9.0}, "Temp": {"min": 21.0, "max": 31.4, "p1": 22.0, "p99": 29.0}}})
