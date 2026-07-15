"""Shared chart styling for every CityHire chart script - one consistent,
polished visual language across the ebook (City Hire brand colors, larger
type, direct data labels instead of relying on gridlines alone)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAVY = "#0C1114"
GREEN = "#009B66"
GREEN_DARK = "#00754D"
BLUE = "#2A7ACC"
SLATE = "#3C5667"
SLATE_LIGHT = "#8FA8B8"
LIGHT = "#F2F5F7"
RED = "#C0392B"
AMBER = "#D98E04"
GRID = "#E7ECEF"
DPI = 240


def apply_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 10.5,
        "axes.edgecolor": "#C3CDD3",
        "axes.linewidth": 0.9,
        "axes.labelcolor": SLATE,
        "axes.labelsize": 9.5,
        "text.color": NAVY,
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "legend.fontsize": 9.5,
        "legend.frameon": False,
    })


def title(ax, text, subtitle=None, pad=16):
    ax.set_title(text, fontsize=13.5, fontweight="bold", color=NAVY, loc="left", pad=pad)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=SLATE, va="bottom")


def hbar_labels(ax, bars, values, fmt="{:.0f}", color=None, inside_threshold=None):
    """Direct value labels at the end of horizontal bars.

    Long bars (>= inside_threshold): label sits INSIDE the bar near its tip,
    anchored so it reads back toward the bar's start (white text on the
    bar's own color).
    Short bars (< inside_threshold): label sits OUTSIDE the bar, past its
    tip, in the axis ink color, so it doesn't get swallowed by white space.
    """
    for bar, v in zip(bars, values):
        w = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        label = fmt.format(v)
        is_short = inside_threshold and abs(w) < inside_threshold
        if is_short:
            # outside the bar: anchor away from zero, text extends further out
            x = w
            ha = "left" if w >= 0 else "right"
            c = color or SLATE
            text = f" {label}" if ha == "left" else f"{label} "
        else:
            # inside the bar: anchor at the tip, text extends back toward zero
            pad = abs(w) * 0.03
            x = w - pad if w >= 0 else w + pad
            ha = "right" if w >= 0 else "left"
            c = "white"
            text = label
        ax.text(x, y, text, va="center", ha=ha, fontsize=8.7, fontweight="bold", color=c)


def vbar_labels(ax, bars, fmt="{:.1f}%"):
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h, fmt.format(h) + "\n",
                 ha="center", va="bottom", fontsize=8.3, fontweight="bold", color=NAVY)
