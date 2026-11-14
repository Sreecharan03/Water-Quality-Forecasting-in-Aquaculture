"""Phase 1b gate for candidate 2: inspect the BCO-DMO salt-marsh pond file on Modal. Nothing is persisted; a description is printed.

    modal run -m modal_jobs.phase1b_bco::run
"""
from __future__ import annotations

import hashlib
import io
import urllib.request

from modal_jobs.common import DATA_MOUNT, VOLUMES, app, data_vol, image

URL = "https://datadocs.bco-dmo.org/dataset/988873/file/7D5YK41uEZBrB6/988873_v1_salt_pond_monitoring.csv"
EXPECTED_MD5 = "7337bc6512134cfef333f9e4edae3bf7"
EXPECTED_COLS = ["datetime_utc", "site", "lat", "lon", "depth", "salinity", "temperature", "DOconc", "DOeqsat", "DOsat", "pH"]


@app.function(image=image, timeout=900, cpu=2.0)
def inspect_bco() -> str:
    import numpy as np
    import pandas as pd
    L = []
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "research-data-check"}), timeout=300).read()
    md5 = hashlib.md5(raw).hexdigest()
    L.append(f"downloaded {len(raw)} bytes; md5 {md5}; matches published: {md5 == EXPECTED_MD5}")
    df = pd.read_csv(io.BytesIO(raw), na_values=["", "nd", "NaN"])
    L.append(f"rows {len(df)}, columns {list(df.columns)}")
    L.append(f"expected columns all present: {all(c in df.columns for c in EXPECTED_COLS)}")
    df["t"] = pd.to_datetime(df["datetime_utc"], errors="coerce", utc=True)
    L.append(f"unparseable timestamps: {int(df['t'].isna().sum())}")
    rho = (1000 + 0.8 * df["salinity"].fillna(df["salinity"].median())) / 1000
    df["DO_mgL"] = df["DOconc"] * 31.998 * rho / 1000
    L += ["", "## per pond"]
    rows = []
    for site, g in df.sort_values("t").groupby("site"):
        g = g.dropna(subset=["t"])
        span_days = (g["t"].max() - g["t"].min()).days
        step = g["t"].diff().median()
        ok_all = g[["DO_mgL", "pH", "temperature"]].notna().all(axis=1).mean()
        rows.append({"site": site, "rows": len(g), "start": g["t"].min().date(), "end": g["t"].max().date(), "span_days": span_days, "median_step": step,
                     "DO_valid%": round(g["DO_mgL"].notna().mean() * 100, 1), "pH_valid%": round(g["pH"].notna().mean() * 100, 1),
                     "temp_valid%": round(g["temperature"].notna().mean() * 100, 1), "all3_valid%": round(ok_all * 100, 1),
                     "rows_vs_full_grid%": round(len(g) / (span_days * 144 + 1) * 100, 1)})
    L.append(pd.DataFrame(rows).to_string(index=False))
    L += ["", "## months with >= 50% of the 10-minute grid holding valid DO, pH and temperature (per pond)"]
    for site, g in df.groupby("site"):
        g = g.dropna(subset=["t"]).copy()
        g["ok"] = g[["DO_mgL", "pH", "temperature"]].notna().all(axis=1)
        g["m"] = g["t"].dt.strftime("%Y-%m")
        cov = g.groupby("m")["ok"].sum() / (g.groupby("m")["t"].agg(lambda s: s.dt.days_in_month.iloc[0]) * 144)
        good = [m for m, v in cov.items() if v >= 0.5]
        L.append(f"- {site}: {len(good)} months: {', '.join(good)}")
    L += ["", "## value ranges (all ponds)"]
    for c in ["DO_mgL", "pH", "temperature", "salinity", "depth"]:
        s = df[c]
        L.append(f"- {c}: min {s.min():.2f}, p5 {s.quantile(.05):.2f}, median {s.median():.2f}, p95 {s.quantile(.95):.2f}, max {s.max():.2f}")
    L += ["", "## daily oxygen range (median of daily max minus min, days with >= 100 valid readings), mg/L"]
    for site, g in df.dropna(subset=["t", "DO_mgL"]).groupby("site"):
        d = g.groupby(g["t"].dt.date)["DO_mgL"].agg(["max", "min", "size"])
        d = d[d["size"] >= 100]
        L.append(f"- {site}: median {np.median(d['max'] - d['min']):.2f}, p90 {np.percentile(d['max'] - d['min'], 90):.2f} (n days {len(d)})")
    low = df.dropna(subset=["DO_mgL"])
    L += ["", "## low oxygen", f"- share of readings below 2 mg/L: {(low['DO_mgL'] < 2).mean()*100:.1f}%; below 3 mg/L: {(low['DO_mgL'] < 3).mean()*100:.1f}%; ponds with any < 2: {int((low.groupby('site')['DO_mgL'].min() < 2).sum())}"]
    # real-data traits: step regularity and gaps
    L += ["", "## gap structure (real-data trait check)"]
    for site, g in df.dropna(subset=["t"]).sort_values("t").groupby("site"):
        dt = g["t"].diff().dropna()
        L.append(f"- {site}: steps equal to 10 min {(dt == pd.Timedelta(minutes=10)).mean()*100:.1f}%; gaps > 1 h: {(dt > pd.Timedelta(hours=1)).sum()}; longest gap {dt.max()}")
    L += ["", "## depth variation (tide), per pond: p5-p95 range of depth (m)"]
    for site, g in df.groupby("site"):
        L.append(f"- {site}: {g['depth'].quantile(.05):.2f} to {g['depth'].quantile(.95):.2f}")
    return "\n".join(L)


@app.local_entrypoint()
def run():
    print(inspect_bco.remote())


@app.function(image=image, volumes=VOLUMES, timeout=600)
def eluru_reference() -> str:
    """Same descriptive statistics for our Eluru development ponds (dev_train + dev_val only)."""
    import json
    from pathlib import Path
    import numpy as np
    import pandas as pd
    data_vol.reload()
    mans = sorted(Path(DATA_MOUNT, "manifests").glob("features_ft-*.json"), key=lambda p: p.stat().st_mtime)
    fv = json.loads(mans[-1].read_text(encoding="utf-8"))["feature_version"]
    smans = sorted(Path(DATA_MOUNT, "manifests").glob("splits_sp-*.json"), key=lambda p: p.stat().st_mtime)
    sv = json.loads(smans[-1].read_text(encoding="utf-8"))["split_version"]
    F = pd.concat([pd.read_parquet(f, columns=["pond", "grid_idx", "ts_ist", "DO_cur", "pH_cur", "Temp_cur"]) for f in sorted(Path(DATA_MOUNT, "features", fv).glob("*.parquet"))])
    a = pd.read_parquet(Path(DATA_MOUNT, "splits", sv, "assignments.parquet"), columns=["pond", "grid_idx", "role"])
    T = F.merge(a, on=["pond", "grid_idx"])
    T = T[T["role"].isin(["dev_train", "dev_val"])]
    L = [f"Eluru dev ponds: {T['pond'].nunique()}, rows {len(T)}, span {T['ts_ist'].min().date()} to {T['ts_ist'].max().date()}"]
    d = T.dropna(subset=["DO_cur"]).groupby(["pond", T["ts_ist"].dt.date])["DO_cur"].agg(["max", "min", "size"])
    d = d[d["size"] >= 60]
    r = d["max"] - d["min"]
    L.append(f"daily DO range (days with >= 60 readings): median {r.median():.2f}, p90 {r.quantile(.9):.2f} mg/L (n days {len(r)})")
    for c, nm in (("DO_cur", "DO mg/L"), ("pH_cur", "pH"), ("Temp_cur", "temperature C")):
        s = T[c]
        L.append(f"{nm}: min {s.min():.2f}, p5 {s.quantile(.05):.2f}, median {s.median():.2f}, p95 {s.quantile(.95):.2f}, max {s.max():.2f}")
    L.append(f"share DO < 2 mg/L: {(T['DO_cur'] < 2).mean()*100:.1f}%; share exactly 0: {(T['DO_cur'] == 0).mean()*100:.2f}%")
    return "\n".join(L)


@app.local_entrypoint()
def reference():
    print(eluru_reference.remote())
