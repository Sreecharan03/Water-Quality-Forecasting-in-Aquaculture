"""Human-readable feature dictionary generated from the same config that builds the features."""
from __future__ import annotations

UNITS = {"DO": "mg/L", "pH": "pH units", "Temp": "°C"}
NAMES = {"DO": "dissolved oxygen", "pH": "pH", "Temp": "water temperature"}
STEP_MIN = 15


def _dur(steps: int) -> str:
    m = steps * STEP_MIN
    return f"{m} min" if m < 60 else f"{m / 60:g} h"


def feature_specs(cfg: dict) -> list[dict]:
    L, cap, ws = cfg["flag_lookback"], cfg["age_cap"], cfg["slope_window"]
    S = []

    def add(name, group, meaning, unit, window, why):
        S.append({"name": name, "group": group, "meaning": meaning, "unit": unit, "window": window, "why_valid": why})

    ok = "uses only readings at or before the origin time"
    for v in cfg["variables"]:
        u, nm = UNITS[v], NAMES[v]
        add(f"{v}_cur", "history", f"Latest {nm} reading at the origin time", u, "origin", "the origin reading itself is known at t")
        for k in cfg["lags"]:
            add(f"{v}_lag{k}", "history", f"{nm} reading {_dur(k)} before the origin", u, f"t-{_dur(k)}", "past reading")
        for w in cfg["windows"]:
            for stat in ("mean", "min", "max", "std"):
                add(f"{v}_{stat}{w}", "rolling", f"{stat} of valid {nm} readings over the last {_dur(w)}", u, f"last {_dur(w)}", ok)
        add(f"{v}_slope{ws}", "rolling", f"Linear trend of {nm} over the last {_dur(ws)}", f"{u} per hour", f"last {_dur(ws)}", ok)
        add(f"{v}_age", "quality", f"Time since the last valid {nm} reading (capped at {_dur(cap)}), in 15-min steps", "steps", "since last valid", ok)
        add(f"{v}_valid_frac{L}", "quality", f"Share of the last {_dur(L)} with a valid {nm} reading", "fraction", f"last {_dur(L)}", ok)
    add("flag_do_now", "quality", "Any FWI DO quality flag on the origin reading (<0.1, jump>2, >10 before noon)", "0/1", "origin", "flag rules use values at or before t")
    add("flag_ph_now", "quality", "Any FWI pH quality flag on the origin reading", "0/1", "origin", "flag rules use values at or before t")
    add("flag_gap_now", "quality", "Origin reading came after a recording gap > 20 min", "0/1", "origin", "gap measured to the previous row")
    add(f"n_flag_do_{L}", "quality", f"Number of DO-flagged readings in the last {_dur(L)}", "count", f"last {_dur(L)}", ok)
    add(f"n_flag_ph_{L}", "quality", f"Number of pH-flagged readings in the last {_dur(L)}", "count", f"last {_dur(L)}", ok)
    add(f"n_flag_gap_{L}", "quality", f"Number of gap-flagged readings in the last {_dur(L)}", "count", f"last {_dur(L)}", ok)
    add(f"present_frac{L}", "quality", f"Share of the last {_dur(L)} time slots that have any recorded row", "fraction", f"last {_dur(L)}", ok)
    add("steps_since_prev_row", "quality", "Time since the previous recorded row (1 = normal 15-min cadence)", "steps", "previous row", "past rows only")
    add("hour_sin", "time", "Sine of the time of day (IST), so 23:45 is close to 00:00", "unitless", "origin", "clock time of the origin")
    add("hour_cos", "time", "Cosine of the time of day (IST)", "unitless", "origin", "clock time of the origin")
    return S


def to_markdown(specs: list[dict], cfg: dict, version: str) -> str:
    L = [f"# Feature dictionary (`{version}`)", "",
         "Origin time `t` = a recorded 15-minute row. Every feature uses only data at or before `t`. "
         f"Targets are the real, valid reading at `t + h` for h in {[f'{h*STEP_MIN} min' for h in cfg['horizons']]}; "
         "if no valid reading exists at that time the target is empty (never interpolated).", "",
         "Groups: **history** (current and lagged readings), **rolling** (trailing statistics), "
         "**quality** (data-quality context; the quality-aware pipeline uses these), **time** (clock).", "",
         "| feature | group | meaning | unit | window | why it is valid at prediction time |", "|---|---|---|---|---|---|"]
    for s in specs:
        L.append(f"| `{s['name']}` | {s['group']} | {s['meaning']} | {s['unit']} | {s['window']} | {s['why_valid']} |")
    L += ["", "## Targets", ""]
    for h in cfg["horizons"]:
        for v in cfg["variables"]:
            L.append(f"- `y_{v}_h{h}`: valid {NAMES[v]} reading ({UNITS[v]}) {_dur(h)} after the origin")
    return "\n".join(L)
