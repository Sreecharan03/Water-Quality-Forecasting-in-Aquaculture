"""Adapter for the BCO-DMO 988873 salt-marsh pond file (Phase 1b-R). Pure functions; no network access here.

Rules (configs/replication_bco.yaml): use the curators' quality-controlled values; missing stays missing; no interpolation;
subsample the 10-minute series at exact :00 and :30 UTC timestamps (30-minute grid).
Time: grid, calendar cutoffs and block days use fixed Eastern Standard Time (UTC-5), so daylight-saving changes cannot
create duplicated or missing local hours. `ny_hour` (true New York local hour) is kept for the day/night check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aquatic_xai.data.clean import VAR_FLAG_COLS
from aquatic_xai.features.build import FLAG_SOURCE_COLS

EST_OFFSET = pd.Timedelta(hours=5)
NOMINAL_MIN = 30


def do_mg_per_l(do_umol_kg: pd.Series, salinity: pd.Series) -> pd.Series:
    """mg/L = umol/kg x 31.998 x rho / 1000 with rho = (1000 + 0.8 x salinity)/1000 kg/L (approximate; salinity only).
    Where salinity is missing, the pooled median salinity is used for the density only."""
    sal = salinity.fillna(salinity.median())
    return do_umol_kg * 31.998 * ((1000.0 + 0.8 * sal) / 1000.0) / 1000.0


def prepare_pond(df: pd.DataFrame) -> pd.DataFrame:
    """df: rows of ONE pond with columns datetime_utc (str), DOconc, salinity, pH, temperature. Returns tidy 10-minute frame (UTC)."""
    out = pd.DataFrame({"t": pd.to_datetime(df["datetime_utc"], utc=True), "DO": df["DO_mgL"].to_numpy(),
                        "pH": df["pH"].to_numpy(), "Temp": df["temperature"].to_numpy()})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def to_grid(pond: pd.DataFrame, nominal: int = NOMINAL_MIN) -> pd.DataFrame:
    """Subsample at exact grid timestamps; build the frame that features.build.compute_features expects."""
    t = pond["t"]
    on_grid = (t.dt.minute % nominal == 0) & (t.dt.second == 0)
    p = pond[on_grid].reset_index(drop=True)
    t0 = p["t"].iloc[0]
    idx = ((p["t"] - t0) / pd.Timedelta(minutes=nominal)).round().astype(int).to_numpy()
    n = int(idx.max()) + 1
    present = np.zeros(n, dtype=bool)
    present[idx] = True
    grid = pd.DataFrame({"present": present})
    utc = t0 + pd.to_timedelta(np.arange(n) * nominal, unit="m")
    grid["ts"] = (utc - EST_OFFSET).tz_localize(None)                       # fixed standard time, naive
    grid["ny_hour"] = utc.tz_convert("America/New_York").hour + utc.tz_convert("America/New_York").minute / 60.0
    grid["utc"] = utc.tz_localize(None)
    for v in ("DO", "pH", "Temp"):
        col = np.full(n, np.nan)
        col[idx] = p[v].to_numpy(dtype=float)
        grid[v] = col
    flag_cols = set(FLAG_SOURCE_COLS) | {c for cs in VAR_FLAG_COLS.values() for c in cs}
    for c in flag_cols:
        grid[c] = False                                                      # this dataset has no quality flags
    return grid
