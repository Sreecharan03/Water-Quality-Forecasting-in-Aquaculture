"""Thesis figures from the AGGREGATE numbers of the sealed final test (docs/experiments/final_test_report.md). No raw data."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BLUE, ORANGE, GREY = "#0072B2", "#E69F00", "#8c8c8c"

# (label, app, now, yesterday) each as (estimate, low, high) with 99% interval; from the final-test report, table A
CELLS = [
    ("Oxygen\n15 min", (0.329, 0.293, 0.365), (0.387, 0.352, 0.428), (1.548, 1.294, 1.846), "pass"),
    ("Oxygen\n1 h", (0.714, 0.628, 0.802), (1.115, 1.017, 1.208), (1.541, 1.287, 1.832), "pass"),
    ("Oxygen\n6 h", (1.655, 1.412, 1.930), (4.889, 4.379, 5.346), (1.520, 1.265, 1.836), "fail"),
    ("Temperature\n1 h", (0.098, 0.087, 0.113), (0.143, 0.126, 0.159), (0.206, 0.170, 0.246), "pass"),
    ("Temperature\n6 h", (0.250, 0.213, 0.291), (0.667, 0.591, 0.741), (0.203, 0.156, 0.246), "fail"),
]
COVER = [("Oxygen 15 min", 94.9, 93.4, 96.2), ("Oxygen 1 h", 94.4, 91.7, 96.6), ("Oxygen 6 h", 91.8, 87.1, 95.6), ("pH 15 min", 99.2, 98.6, 99.6),
         ("pH 1 h", 98.9, 98.0, 99.5), ("pH 6 h", 97.3, 93.2, 99.5), ("Temp 15 min", 98.7, 98.0, 99.3), ("Temp 1 h", 98.5, 97.2, 99.4), ("Temp 6 h", 97.3, 94.8, 99.3)]
ALERT = [("next hour", 0.968, 0.568, 0.955, 0.953), ("next 3 hours", 0.930, 0.616, 0.723, 0.896), ("next 6 hours", 0.886, 0.661, 0.612, 0.831)]


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def fig_forecasts() -> bytes:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [3, 2]})
    for ax, idx, title, unit in ((axes[0], [0, 1, 2], "Oxygen", "mg/L"), (axes[1], [3, 4], "Water temperature", "°C")):
        x = np.arange(len(idx))
        for j, (name, col, key) in enumerate((("The app", BLUE, 1), ("Same as now", GREY, 2), ("Same time yesterday", ORANGE, 3))):
            est = np.array([CELLS[i][key][0] for i in idx])
            lo = np.array([CELLS[i][key][1] for i in idx])
            hi = np.array([CELLS[i][key][2] for i in idx])
            ax.bar(x + (j - 1) * 0.26, est, 0.24, color=col, label=name, yerr=[est - lo, hi - est], capsize=2, error_kw={"lw": 1})
        ax.set_xticks(x)
        ax.set_xticklabels([CELLS[i][0].split("\n")[1] + ("\n(failed)" if CELLS[i][4] == "fail" else "\n(passed)") for i in idx])
        ax.set_title(f"{title}: average miss ({unit}), lower is better", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Sealed final test on four never-seen ponds (bars: estimate; lines: 99% interval)", fontsize=11)
    fig.tight_layout()
    return _png(fig)


def fig_coverage() -> bytes:
    fig, ax = plt.subplots(figsize=(7.5, 4))
    y = np.arange(len(COVER))[::-1]
    for yi, (lab, est, lo, hi) in zip(y, COVER):
        ax.plot([lo, hi], [yi, yi], color=BLUE, lw=2)
        ax.plot(est, yi, "o", color=BLUE)
    ax.axvline(90, color=ORANGE, lw=2, label="Target: 90%")
    ax.axvspan(87, 93, color=ORANGE, alpha=0.12, label="Pre-registered band 87% to 93%")
    ax.set_yticks(y)
    ax.set_yticklabels([c[0] for c in COVER])
    ax.set_xlabel("Share of real values inside the 'likely between' range (%), with 99% interval")
    ax.set_xlim(84, 100.5)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Ranges never fell below target, but were usually wider than needed", fontsize=10)
    fig.tight_layout()
    return _png(fig)


def fig_alert() -> bytes:
    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = np.arange(len(ALERT))
    for j, (name, col) in enumerate((("The app's chance", BLUE), ("Same window yesterday", ORANGE), ("Trend extrapolation", "#009E73"), ("Current level", GREY))):
        ax.bar(x + (j - 1.5) * 0.2, [a[1 + j] for a in ALERT], 0.19, color=col, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels([a[0] for a in ALERT])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Average precision (1.0 = perfect)")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Low-oxygen warning: ranking of risky moments, sealed ponds", fontsize=10)
    fig.tight_layout()
    return _png(fig)


def all_figures() -> dict[str, bytes]:
    return {"fig1_final_test_forecasts.png": fig_forecasts(), "fig2_final_test_ranges.png": fig_coverage(), "fig3_final_test_alert.png": fig_alert()}
