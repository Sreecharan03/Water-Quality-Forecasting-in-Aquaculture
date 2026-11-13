"""Cleaning audit figures (matplotlib, headless). Raw values are shown with their status."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

LABELS = {"DO": "DO (mg/L)", "pH": "pH", "Temp": "Temperature (°C)"}


ROLE_COLORS = {"dev_train": "#4c72b0", "dev_val": "#55a868", "seen_pond_test": "#c44e52",
               "unseen_pond_test": "#8172b2", "sealed_pond_unused": "#cccccc", "embargo": "#ffffff"}


def plot_split(a: pd.DataFrame, info: dict, path: Path) -> None:
    """Gantt chart: one row per pond; colours are roles. Uses timestamps and roles only (no sensor values)."""
    ponds = sorted(a["pond"].unique())
    fig, ax = plt.subplots(figsize=(13, 0.45 * len(ponds) + 2))
    d = a[~a["is_warmup"]]
    for i, p in enumerate(ponds):
        g = d[d["pond"] == p]
        for role, color in ROLE_COLORS.items():
            if role == "embargo":      # spans the whole validation window; drawing it would hide that window
                continue
            r = g[g["role"] == role]
            if len(r) == 0:
                continue
            ax.barh(i, (r["ts_ist"].max() - r["ts_ist"].min()).total_seconds() / 86400,
                    left=matplotlib.dates.date2num(r["ts_ist"].min()), color=color, edgecolor="none", height=0.6)
    ax.set_yticks(range(len(ponds)))
    ax.set_yticklabels([f"{p}{' *' if p in info['sealed_ponds'] else ''}" for p in ponds], fontsize=8)
    for c in (info["cutoff_train_end"], info["cutoff_val_end"]):
        ax.axvline(matplotlib.dates.date2num(pd.Timestamp(c)), color="black", ls="--", lw=1)
    ax.xaxis_date()
    handles = [matplotlib.patches.Patch(color=v, label=k) for k, v in ROLE_COLORS.items() if k != "embargo"]
    ax.legend(handles=handles, loc="upper left", fontsize=8, ncol=3)
    ax.set_title("Split design: roles by pond and time (* = sealed unseen-pond test; dashed = calendar cutoffs; embargo not drawn)")
    fig.autofmt_xdate()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def plot_cleaning_audit(proc_by_pond: dict, ponds: list[str], path: Path, event_date: str) -> None:
    fig, axes = plt.subplots(3, len(ponds), figsize=(6 * len(ponds), 9), squeeze=False, sharex="col")
    for j, pond in enumerate(ponds):
        p = proc_by_pond[pond]
        for i, v in enumerate(("DO", "pH", "Temp")):
            ax = axes[i][j]
            ok = p[f"{v}_status"] == "ok"
            ax.plot(p.loc[ok, "ts_ist"], p.loc[ok, v], ".", ms=1.5, color="#4c72b0", label="valid")
            for st, color, mk in (("zero_artifact", "#d62728", "x"), ("dup_conflict", "#ff7f0e", "s")):
                m = p[f"{v}_status"] == st
                if m.any():
                    ax.plot(p.loc[m, "ts_ist"], p.loc[m, f"{v}_raw"], mk, ms=4, color=color, label=st)
            flag_cols = {"DO": "flag_do_jump", "pH": "flag_ph_range"}.get(v)
            if flag_cols is not None:
                m = ok & p[flag_cols]
                if m.any():
                    ax.plot(p.loc[m, "ts_ist"], p.loc[m, v], "o", ms=3, mfc="none", color="#2ca02c", label=flag_cols)
            ax.axvline(pd.Timestamp(event_date), color="grey", ls="--", lw=1)
            ax.set_ylabel(LABELS[v])
            if i == 0:
                ax.set_title(pond)
            if j == 0:
                ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("Cleaning audit: raw values by status (dashed line = calibration event)")
    fig.autofmt_xdate()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
