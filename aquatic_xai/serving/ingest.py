"""Turn what a pond owner pastes or uploads into the 15-minute grid the models expect, with plain-language messages.

Rules are the same as the research pipeline (Phase 2 and 3): exact zeros are treated as sensor faults, readings outside physical limits are
ignored, conflicting duplicate times are ignored, readings are placed on a 15-minute grid within 3 minutes, nothing is ever filled in or invented.
"""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd

from aquatic_xai.features.build import FLAG_SOURCE_COLS, make_grid

LIMITS = {"DO": (0.0, 30.0), "pH": (0.0, 14.0), "Temp": (0.0, 45.0)}
NICE = {"DO": "oxygen", "pH": "pH", "Temp": "temperature"}
MIN_HISTORY_STEPS = 100            # 25 hours at 15 minutes: yesterday's pattern needs a full day plus margin
MAX_ROWS = 6000
STUCK_STEPS = 8                    # 2 hours of identical readings
ALIASES = {"time": ["time", "timestamp", "date", "datetime", "date_time", "reading time", "when"],
           "DO": ["oxygen", "do", "dissolved oxygen", "dissolved_oxygen", "do_mg_l", "do (mg/l)", "oxygen (mg/l)", "o2"],
           "pH": ["ph", "acidity", "acidity (ph)"],
           "Temp": ["temperature", "temp", "water temperature", "water_temp", "temp_c", "temperature (c)", "temperature (°c)", "water temperature (°c)"]}


class InputProblem(Exception):
    """A problem the owner can fix; the message is written for them."""


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", str(h).strip().lower())


def parse_text(text: str) -> pd.DataFrame:
    if not text or not text.strip():
        raise InputProblem("We did not receive any readings. Paste your readings or upload a file.")
    if len(text) > 2_000_000:
        raise InputProblem("That file is too large. Please send at most the last 3 days of readings.")
    first = text.strip().splitlines()[0]
    sep = max([",", ";", "\t", "|"], key=lambda s: first.count(s))
    if first.count(sep) == 0:
        raise InputProblem("We could not find separate columns. Please use a spreadsheet with columns: time, oxygen, pH, temperature.")
    df = pd.read_csv(io.StringIO(text.strip()), sep=sep, dtype=str, skipinitialspace=True)
    return rename_columns(df)


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {_norm(c): c for c in df.columns}
    out, missing = {}, []
    for key, names in ALIASES.items():
        hit = next((cols[n] for n in names if n in cols), None)
        if hit is None:
            missing.append({"time": "a time column", "DO": "an oxygen column", "pH": "a pH column", "Temp": "a temperature column"}[key])
        else:
            out[key] = df[hit]
    if missing:
        raise InputProblem("We could not find " + ", ".join(missing) + ". Please name your columns: time, oxygen, pH, temperature (see the template).")
    return pd.DataFrame(out)


def _parse_time(s: pd.Series, issues: list[dict]) -> pd.Series:
    t = pd.to_datetime(s, errors="coerce", format="ISO8601")
    if t.isna().mean() > 0.5:
        t = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if t.notna().any():
            issues.append({"level": "info", "text": "We read dates as day/month/year. Please check that the latest reading time shown below is right."})
    return t


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], dict]:
    """Returns (grid, issues, summary). Raises InputProblem if the data cannot be used at all."""
    issues: list[dict] = []
    if len(df) > MAX_ROWS:
        raise InputProblem(f"That is {len(df):,} readings. Please send at most the last {MAX_ROWS:,} (about 3 days at one reading every 15 minutes, more if readings are more frequent).")
    t = _parse_time(df["time"], issues)
    bad_t = int(t.isna().sum())
    d = pd.DataFrame({"ts_ist": t})
    for v in ("DO", "pH", "Temp"):
        d[v] = pd.to_numeric(df[v].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    n_in = len(d)
    d = d[d["ts_ist"].notna()].copy()
    if bad_t:
        issues.append({"level": "warn", "text": f"{bad_t} rows had a time we could not read, so they were left out."})
    if d.empty:
        raise InputProblem("We could not read any of the times. Please use times like 2026-01-12 09:15.")
    if getattr(d["ts_ist"].dt, "tz", None) is not None:
        d["ts_ist"] = d["ts_ist"].dt.tz_localize(None)
    # physical limits and zeros (zeros are sensor faults in this project's data)
    for v in ("DO", "pH", "Temp"):
        x = d[v]
        zeros, outside = int((x == 0).sum()), int(((x < LIMITS[v][0]) | (x > LIMITS[v][1])).sum())
        d.loc[(x == 0) | (x < LIMITS[v][0]) | (x > LIMITS[v][1]), v] = np.nan
        nonnum = int(df[v].notna().sum() - x.notna().sum())
        if zeros:
            issues.append({"level": "warn", "text": f"{zeros} {NICE[v]} readings were exactly 0. A sensor often shows 0 when it is not working, so we ignored them."})
        if outside > 0:
            issues.append({"level": "warn", "text": f"{outside} {NICE[v]} readings were outside what is physically possible ({LIMITS[v][0]:g} to {LIMITS[v][1]:g}) and were ignored."})
        if nonnum > 0:
            issues.append({"level": "warn", "text": f"{nonnum} {NICE[v]} entries were not numbers and were ignored."})
    # duplicate times: identical collapse, conflicting values are ignored
    dup = d.duplicated("ts_ist", keep=False)
    if dup.any():
        agg = d[dup].groupby("ts_ist")[["DO", "pH", "Temp"]].agg(lambda s: s.dropna().iloc[0] if s.dropna().nunique() == 1 else np.nan)
        conflicts = int(d[dup].groupby("ts_ist")[["DO", "pH", "Temp"]].agg(lambda s: s.dropna().nunique() > 1).any(axis=1).sum())
        d = pd.concat([d[~dup], agg.reset_index()], ignore_index=True)
        if conflicts:
            issues.append({"level": "warn", "text": f"{conflicts} times appeared twice with different values. We ignored those values because we cannot tell which one is right."})
    d = d.sort_values("ts_ist").reset_index(drop=True)
    for c in FLAG_SOURCE_COLS:
        d[c] = False
    grid, not_placed = make_grid(d, 15, 3)          # the same placement rule as the research pipeline: within 3 minutes, first reading per slot
    if not_placed:
        issues.append({"level": "info", "text": f"{not_placed} readings did not fall within 3 minutes of a 15-minute step (or were extra readings in the same step) and were not used."})
    n = len(grid)
    first, last = grid["ts"].iloc[0], grid["ts"].iloc[-1]
    hours = (last - first).total_seconds() / 3600
    has = {v: int(grid[v].notna().sum()) for v in ("DO", "pH", "Temp")}
    last_valid = {v: (grid.loc[grid[v].notna(), "ts"].max() if has[v] else None) for v in has}
    summary = {"Readings used": f"{int(grid['present'].sum()):,} of {n_in:,}", "Time covered": f"{hours:.0f} hours", "First reading": first.strftime("%d %b %Y, %H:%M"),
               "Latest reading": last.strftime("%d %b %Y, %H:%M"), "Readings missing in between": f"{int((~grid['present']).sum()):,}"}
    if n < MIN_HISTORY_STEPS:
        raise InputProblem(f"We need at least 25 hours of readings (about {MIN_HISTORY_STEPS} readings every 15 minutes) so the computer can see the daily pattern. You gave us {hours:.0f} hours.")
    # stuck sensors
    for v in ("DO", "pH"):
        tail = grid[v].tail(STUCK_STEPS)
        if tail.notna().all() and tail.nunique() == 1:
            issues.append({"level": "warn", "text": f"The {NICE[v]} sensor shows exactly the same number for the last {STUCK_STEPS // 4} hours. That usually means the sensor is stuck, so we will not forecast {NICE[v]}."})
            summary[f"stuck_{v}"] = True
    last24 = grid.tail(96)
    for v in ("DO", "pH", "Temp"):
        share = last24[v].notna().mean()
        if share < 0.5:
            issues.append({"level": "warn", "text": f"Less than half of the last 24 hours of {NICE[v]} readings are available, so we will not forecast {NICE[v]}."})
            summary[f"sparse_{v}"] = True
    summary["_last_valid"] = {v: (str(x) if x is not None else None) for v, x in last_valid.items()}
    return grid, issues, summary


def example_csv() -> str:
    """Made-up numbers for a demo pond (NOT real data): oxygen falls overnight, rises in daylight."""
    rng = np.random.RandomState(7)
    t = pd.date_range("2026-01-09 15:00", periods=4 * 30 + 1, freq="15min")           # ends in the evening, so the night-time dip is still ahead
    hour = t.hour + t.minute / 60
    do = 6.5 + 4.5 * np.sin((hour - 9) / 24 * 2 * np.pi) - 0.02 * np.arange(len(t)) / 4 + rng.normal(0, 0.12, len(t))
    ph = 8.3 + 0.35 * np.sin((hour - 10) / 24 * 2 * np.pi) + rng.normal(0, 0.02, len(t))
    temp = 25.5 + 1.4 * np.sin((hour - 10) / 24 * 2 * np.pi) + rng.normal(0, 0.05, len(t))
    do = np.clip(do, 0.4, None)
    out = pd.DataFrame({"time": t.strftime("%Y-%m-%d %H:%M"), "oxygen": np.round(do, 2), "pH": np.round(ph, 2), "temperature": np.round(temp, 1)})
    return out.to_csv(index=False)


def template_csv() -> str:
    return "time,oxygen,pH,temperature\n2026-01-10 05:00,3.1,8.05,25.2\n2026-01-10 05:15,3.0,8.04,25.1\n"
