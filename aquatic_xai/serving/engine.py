"""Prediction engine: grid of readings in, plain-language forecasts, ranges, low-oxygen risk and reasons out.

Uses the SAME feature code as the research pipeline (features.build.compute_features, features.daily, alerts.labels), so the numbers the app
shows can be checked against the offline pipeline (see the parity test in modal_jobs/phase10.py).

Bundle layout (written by modal_jobs/phase10.py):
  manifest.json   cells, columns, ranges, calibrators, evidence, versions
  models/*.txt    LightGBM boosters (text format)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from aquatic_xai.alerts.labels import window_labels
from aquatic_xai.features.build import compute_features
from aquatic_xai.features.daily import daily_features
from aquatic_xai.serving import plain

INPUT_DECIMALS = 8
PHYS = {"DO": (0.0, 30.0), "pH": (0.0, 14.0), "Temp": (0.0, 45.0)}


class Engine:
    def __init__(self, bundle_dir: str | Path):
        import lightgbm as lgb
        self.dir = Path(bundle_dir)
        self.m = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self._boosters: dict[str, list] = {}
        for key, c in list(self.m["cells"].items()) + [(f"A_{w}", a) for w, a in self.m["alerts"].items()]:
            if c.get("files"):
                self._boosters[key] = [lgb.Booster(model_file=str(self.dir / "models" / f)) for f in c["files"]]

    @property
    def version(self) -> str:
        return self.m["bundle_version"]

    # ----------------------------------------------------------------------------------------------- features
    def _row(self, grid: pd.DataFrame) -> dict:
        fcfg, day = self.m["features_cfg"], self.m["day_steps"]
        feats = compute_features(grid, fcfg, 15)
        tab = pd.DataFrame({"grid_idx": np.arange(len(grid)), "DO_cur": grid["DO"].to_numpy(), "pH_cur": grid["pH"].to_numpy(), "Temp_cur": grid["Temp"].to_numpy()})
        daily = daily_features(tab, fcfg["horizons"], day=day).iloc[-1]
        row = {**feats.iloc[-1].to_dict(), **daily.to_dict()}
        for w in (int(k) for k in self.m["alerts"]):
            row[f"ydaymin_W{w}"] = float(window_labels(tab, w, self.m["alert_threshold_mg_l"], day)[1][-1])
        return row

    @staticmethod
    def _vec(cols: list[str], row: dict) -> np.ndarray:
        """Model inputs, rounded to 8 decimals. Rolling statistics carry ~1e-12 floating-point noise that depends on how much history was
        fed in; trees can split on that noise, so training and serving both round (see PHASE_10.md, 'train/serve skew')."""
        return np.round(np.array([row.get(c, np.nan) for c in cols], dtype=float), INPUT_DECIMALS)

    # ----------------------------------------------------------------------------------------------- forecasts
    def _cell(self, var: str, h: int, row: dict, hour: int, blocked: str | None) -> dict:
        c = self.m["cells"][f"{var}_{h}"]
        base = {"variable": var, "title": plain.VAR_TITLE[var], "unit": plain.UNIT[var], "ahead_steps": h, "when": plain.HORIZON_TITLE[h]}
        cur = row.get(f"{var}_cur", np.nan)
        if blocked:
            return {**base, "status": "no_forecast", "reason": blocked}
        if np.isnan(cur):
            return {**base, "status": "no_forecast", "reason": f"The latest {plain.VAR_NAME[var]} reading is missing, so we cannot forecast it."}
        yd = row.get(f"{var}_yday_tgt_h{h}", np.nan)
        note = None
        if c["method"] == "same_as_now":
            value = float(cur)
        elif c["method"] == "yesterday":
            if np.isnan(yd):
                value, note = float(cur), "Yesterday's reading for that time was missing, so we used the latest reading instead."
            else:
                value = float(yd)
        else:
            anchor = float(cur) if c["anchor"] == "persistence" else float(yd if not np.isnan(yd) else cur)
            if c["anchor"] == "yesterday" and np.isnan(yd):
                note = "Yesterday's reading for that time was missing, so we started from the latest reading instead."
            x = self._vec(c["columns"], row)
            if c["anchor"] == "yesterday":
                x = np.round(np.append(x, anchor - cur), INPUT_DECIMALS)
            X = x[None, :]
            res = np.mean([b.predict(X)[0] for b in self._boosters[f"{var}_{h}"]])
            value = anchor + float(res)
        r = c["range"]
        use_dn = r["use"] == "daynight"
        d0, d1 = self.m["day_hours"]
        q = (r["day"] if d0 <= hour < d1 else r["night"]) if use_dn else r["plain"]
        lo, hi = max(PHYS[var][0], value - q), min(PHYS[var][1], value + q)
        out = {**base, "status": "ok", "value": round(value, 3), "value_text": plain.format_value(var, value),
               "low": round(lo, 3), "high": round(hi, 3), "range_text": f"{plain.format_value(var, lo)} to {plain.format_value(var, hi)}",
               "method": c["method"], "story": plain.method_story(var, h, c["method"], c.get("mae_method"), c.get("mae_simple")), "note": note, "reasons": []}
        if c["method"] == "model":
            names = list(c["columns"]) + (["anchor_gap"] if c["anchor"] == "yesterday" else [])
            contrib = np.mean([b.predict(X, pred_contrib=True)[0][:-1] for b in self._boosters[f"{var}_{h}"]], axis=0)
            out["reasons"] = [{**r_, "sentence": plain.reason_sentence(r_, plain.UNIT[var], False)} for r_ in plain.group_reasons(names, contrib.tolist())]
            out["reasons_note"] = None if c.get("explain_validated") else ("These reasons were less steady in our tests, so treat them as a rough guide only.")
        return out

    # ----------------------------------------------------------------------------------------------- alert
    def _alert(self, row: dict, blocked: str | None) -> dict:
        res = {"title": "Chance of very low oxygen", "threshold_text": f"below {self.m['alert_threshold_mg_l']:g} mg/L", "experimental": True, "windows": []}
        for w, a in sorted(self.m["alerts"].items(), key=lambda kv: int(kv[0])):
            wi = int(w)
            item = {"window": plain.WINDOW_WORDS[wi], "steps": wi}
            if blocked or np.isnan(row.get("DO_cur", np.nan)):
                item.update({"status": "no_forecast", "reason": blocked or "The latest oxygen reading is missing, so we cannot estimate this."})
            else:
                X = self._vec(a["columns"], row)[None, :]
                p_raw = float(np.mean([b.predict(X)[0] for b in self._boosters[f"A_{w}"]]))
                p_cal = float(np.interp(p_raw, a["calib"]["x"], a["calib"]["y"]))
                contrib = np.mean([b.predict(X, pred_contrib=True)[0][:-1] for b in self._boosters[f"A_{w}"]], axis=0)
                reasons = plain.group_reasons(a["columns"], contrib.tolist())
                item.update({"status": "ok", "p_raw": round(p_raw, 4), "percent": int(round(p_cal * 100)), "level": plain.risk_word(p_cal, a["high_cal"]),
                             "reasons": [{**r_, "sentence": plain.reason_sentence(r_, "", True)} for r_ in reasons],
                             "reasons_note": None if a.get("explain_validated") else "These reasons were less steady in our tests."})
            res["windows"].append(item)
        return res

    # ----------------------------------------------------------------------------------------------- input-range guard
    def _range_guard(self, row: dict) -> tuple[dict, list[str]]:
        """Readings far outside what the models learned from are not forecast (trees extrapolate flatly); readings near the edge get a warning."""
        hard, soft = {}, []
        for v, r in (self.m.get("training_range") or {}).items():
            cur = row.get(f"{v}_cur", np.nan)
            if np.isnan(cur):
                continue
            span = (r["max"] - r["min"]) or 1.0
            lo, hi = r["min"] - 0.1 * span, r["max"] + 0.1 * span
            seen = f"{plain.format_value(v, r['min'])} to {plain.format_value(v, r['max'])}"
            if cur < lo or cur > hi:
                hard[v] = (f"Your latest {plain.VAR_NAME[v]} reading ({plain.format_value(v, cur)}) is far outside what this computer learned from ({seen}), "
                           "so we will not forecast it. It was built for ponds like the ones it was trained on.")
            elif cur < r["p1"] or cur > r["p99"]:
                soft.append(f"Your latest {plain.VAR_NAME[v]} reading ({plain.format_value(v, cur)}) is at the edge of what this computer learned from ({seen}). Be extra careful with its {plain.VAR_NAME[v]} forecasts.")
        return hard, soft

    # ----------------------------------------------------------------------------------------------- public
    def predict(self, grid: pd.DataFrame, summary: dict) -> dict:
        row = self._row(grid)
        hour = int(grid["ts"].iloc[-1].hour)
        hard, soft = self._range_guard(row)
        blocked = {v: (f"The {plain.VAR_NAME[v]} sensor looks stuck, so we will not forecast it." if summary.get(f"stuck_{v}")
                       else (f"Too many {plain.VAR_NAME[v]} readings are missing in the last 24 hours." if summary.get(f"sparse_{v}") else hard.get(v))) for v in ("DO", "pH", "Temp")}
        forecasts = {v: [self._cell(v, h, row, hour, blocked[v]) for h in (1, 4, 24) if f"{v}_{h}" in self.m["cells"]] for v in ("DO", "pH", "Temp")}
        latest = {v: (None if np.isnan(row.get(f"{v}_cur", np.nan)) else float(row[f"{v}_cur"])) for v in ("DO", "pH", "Temp")}
        return {"model_version": self.version, "forecasts": forecasts, "alert": self._alert(row, blocked["DO"]), "latest": latest, "warnings": soft + list(hard.values()),
                "made_at": grid["ts"].iloc[-1].strftime("%d %b %Y, %H:%M")}
