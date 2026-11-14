"""Plain-language wording for the app. No jargon: every technical input name becomes a sentence a pond owner understands."""
from __future__ import annotations

import re

VAR_NAME = {"DO": "oxygen", "pH": "acidity (pH)", "Temp": "water temperature"}
VAR_TITLE = {"DO": "Oxygen", "pH": "Acidity (pH)", "Temp": "Water temperature"}
UNIT = {"DO": "mg/L", "pH": "", "Temp": "°C"}
HORIZON_WORDS = {1: "in 15 minutes", 4: "in 1 hour", 24: "in 6 hours"}
HORIZON_TITLE = {1: "15 minutes from now", 4: "1 hour from now", 24: "6 hours from now"}
WINDOW_WORDS = {4: "the next hour", 12: "the next 3 hours", 24: "the next 6 hours"}


def _dur(steps: int) -> str:
    m = steps * 15
    return f"{m} minutes" if m < 60 else (f"{m // 60} hour" + ("s" if m // 60 != 1 else ""))


def phrase(feature: str) -> str:
    """Short phrase for one model input, e.g. 'oxygen right now'."""
    if feature in ("hour_sin", "hour_cos"):
        return "the time of day"
    if feature == "anchor_gap":
        return "how different yesterday's reading is from the latest reading"
    m = re.fullmatch(r"ydaymin_W(\d+)", feature)
    if m:
        return "the lowest oxygen in the same hours yesterday"
    m = re.fullmatch(r"(DO|pH|Temp)_(.+)", feature)
    if not m:
        return feature.replace("_", " ")
    v, rest = m.group(1), m.group(2)
    n = VAR_NAME[v]
    if rest == "cur":
        return f"{n} right now"
    if (mm := re.fullmatch(r"lag(\d+)", rest)):
        return f"{n} {_dur(int(mm.group(1)))} ago"
    if (mm := re.fullmatch(r"(mean|min|max|std)(\d+)", rest)):
        kind, w = mm.group(1), int(mm.group(2))
        what = {"mean": "the average", "min": "the lowest", "max": "the highest", "std": "how much it has been moving up and down:"}[kind]
        return f"{what} {n} over the last {_dur(w)}" if kind != "std" else f"how much {n} has moved up and down over the last {_dur(w)}"
    if rest.startswith("slope"):
        return f"how fast {n} has been rising or falling in the last 3 hours"
    if rest == "d1":
        return f"{n} at this time yesterday"
    if (mm := re.fullmatch(r"d(mean|min|max)96", rest)):
        return {"mean": "the average", "min": "the lowest", "max": "the highest"}[mm.group(1)] + f" {n} over the last 24 hours"
    if re.fullmatch(r"yday_tgt_h\d+", rest):
        return f"{n} yesterday, at the time we are predicting"
    return feature.replace("_", " ")


def group_reasons(names: list[str], contrib: list[float], top: int = 3) -> list[dict]:
    """Merge inputs that mean the same thing (sin and cos of the hour), sort by size, return the biggest few as plain reasons."""
    agg: dict[str, float] = {}
    for n, c in zip(names, contrib):
        agg[phrase(n)] = agg.get(phrase(n), 0.0) + float(c)
    items = sorted(agg.items(), key=lambda kv: -abs(kv[1]))[:top]
    return [{"reason": k, "direction": "up" if v > 0 else "down", "size": abs(v)} for k, v in items]


def reason_sentence(r: dict, unit: str, alert: bool) -> str:
    verb = "raises" if r["direction"] == "up" else "lowers"
    thing = "the chance of low oxygen" if alert else "the forecast"
    return f"{r['reason'][0].upper() + r['reason'][1:]} {verb} {thing}."


def format_value(var: str, x: float) -> str:
    if var == "pH":
        return f"{x:.2f}"
    return f"{x:.1f} {UNIT[var]}".strip()


def method_story(var: str, h: int, method: str, mae: float | None, mae_simple: float | None) -> str:
    """One honest sentence on where the number came from and how it did in testing."""
    unit = UNIT[var]
    if method == "model":
        s = "This number comes from a trained computer model."
        if mae is not None and mae_simple is not None:
            s += f" In our tests on ponds the model had never seen, it missed by about {mae:.2f} {unit}".rstrip() + f", and a plain guess missed by about {mae_simple:.2f} {unit}".rstrip() + "."
        return s
    if method == "same_as_now":
        return ("We simply repeated the latest reading. In our tests, trained models did not do clearly better than this for "
                f"{VAR_NAME[var]} {HORIZON_WORDS[h]}, so we do not pretend they do.")
    return ("We used the reading from the same time yesterday. In our tests, this simple guess was as good as, or better than, the trained models for "
            f"{VAR_NAME[var]} {HORIZON_WORDS[h]}.")


def risk_word(p_cal: float, high_cal: float) -> str:
    """Plain risk word from the calibrated chance. `high_cal` is the level at which we call it a high chance."""
    if p_cal >= high_cal:
        return "High chance"
    if p_cal >= 0.10:
        return "Some chance"
    return "Low chance"


DISCLAIMER = ("This is a research demonstration. It can be wrong. It is not a safety device: keep using your own sensors, alarms and judgement. "
              "It was tested on one farm region in a cool season (Eluru, India), so it may not suit other places or seasons.")
