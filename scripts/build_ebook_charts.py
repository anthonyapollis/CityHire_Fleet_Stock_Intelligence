"""Generate the polished chart images used in the CityHire ebook."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from ml.chart_style import (apply_style, title, hbar_labels, vbar_labels,
                             NAVY, GREEN, GREEN_DARK, BLUE, SLATE, SLATE_LIGHT, RED, AMBER, GRID, DPI)

RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
IMG = ROOT / "docs" / "images"
IMG.mkdir(parents=True, exist_ok=True)
apply_style()

# =============================================================================
# 1) Workshop % / In-service trend
# =============================================================================
trend = pd.read_csv(PROC / "monthly_fleet_trend.csv")
fig, ax = plt.subplots(figsize=(9, 4.4), dpi=DPI)
x = list(range(len(trend)))
util = trend["utilisation_pct"].tolist()
in_service = (100 - trend["workshop_pct"]).tolist()

ax.fill_between(x, in_service, 60, color=BLUE, alpha=0.06)
ax.plot(x, util, color=GREEN, linewidth=2.8, marker="o", markersize=6,
        markerfacecolor="white", markeredgewidth=2, label="Utilisation %", zorder=4)
ax.plot(x, in_service, color=BLUE, linewidth=2.8, marker="o", markersize=6,
        markerfacecolor="white", markeredgewidth=2, label="In-Service %", zorder=4)
ax.axhline(60, color=RED, linestyle=(0, (5, 3)), linewidth=1.1, alpha=0.55)
ax.axhline(85, color=RED, linestyle=(0, (5, 3)), linewidth=1.1, alpha=0.55)
ax.text(0.15, 61.5, "60% target", fontsize=8, color=RED, ha="left", style="italic")
ax.text(0.15, 86.5, "85% target", fontsize=8, color=RED, ha="left", style="italic")
# endpoint callouts
ax.annotate(f"{util[-1]:.1f}%", (x[-1], util[-1]), xytext=(10, 6), textcoords="offset points",
            fontsize=10, fontweight="bold", color=GREEN_DARK)
ax.annotate(f"{in_service[-1]:.1f}%", (x[-1], in_service[-1]), xytext=(10, 6), textcoords="offset points",
            fontsize=10, fontweight="bold", color=BLUE)
ax.set_xticks(x)
ax.set_xticklabels([m[2:] for m in trend["month"]])
ax.set_xlim(-0.3, len(x) + 0.6)
ax.set_ylim(0, 105)
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
title(ax, "12-Month Trend: Utilisation vs In-Service %")
ax.legend(loc="lower right", bbox_to_anchor=(0.98, 0.02))
ax.grid(axis="y", color=GRID, linewidth=0.9)
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(IMG / "trend_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 2) Capex variance by category (top 10 by absolute variance)
# =============================================================================
capex = pd.read_csv(PROC / "capex_vs_budget_by_category.csv")
capex = capex.reindex(capex["ytd_variance_gbp"].abs().sort_values(ascending=False).index).head(10)
capex = capex.sort_values("ytd_variance_gbp")
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=DPI)
colors = [RED if v > 0 else GREEN for v in capex["ytd_variance_gbp"]]
bars = ax.barh(capex["category"], capex["ytd_variance_gbp"] / 1000, color=colors, height=0.62,
                zorder=3, edgecolor="white", linewidth=0.6)
hbar_labels(ax, bars, capex["ytd_variance_gbp"] / 1000, fmt="£{:+.0f}k", inside_threshold=18)
ax.axvline(0, color=NAVY, linewidth=1.1, zorder=2)
ax.set_xlabel("YTD variance, £000s  (actual − budget)")
title(ax, "Capex Variance — Top 10 Categories by Magnitude",
      subtitle="Red = over budget · Green = under budget")
ax.grid(axis="x", color=GRID, linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
xmin, xmax = ax.get_xlim()
ax.set_xlim(xmin - 8, xmax + 8)
plt.tight_layout()
plt.savefig(IMG / "capex_variance_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 3) ROI leaderboard
# =============================================================================
roi = pd.read_csv(PROC / "roi_by_category.csv").sort_values("est_roi_pct", ascending=True).tail(10)
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=DPI)
bars = ax.barh(roi["category"], roi["est_roi_pct"], color=GREEN, height=0.62,
                zorder=3, edgecolor="white", linewidth=0.6)
hbar_labels(ax, bars, roi["est_roi_pct"], fmt="{:.0f}%", inside_threshold=40)
ax.set_xlabel("Estimated annual ROI (%)")
title(ax, "Top 10 Categories by Estimated ROI",
      subtitle="Estimated annual hire revenue ÷ capex outlay")
ax.grid(axis="x", color=GRID, linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
ax.set_xlim(0, roi["est_roi_pct"].max() * 1.12)
plt.tight_layout()
plt.savefig(IMG / "roi_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 4) Depot comparison (utilisation vs workshop)
# =============================================================================
depot = pd.read_csv(PROC / "depot_summary.csv").sort_values("util_pct", ascending=False)
fig, ax = plt.subplots(figsize=(9, 4.4), dpi=DPI)
width = 0.36
xpos = range(len(depot))
b1 = ax.bar([p - width / 2 for p in xpos], depot["util_pct"], width=width, color=GREEN,
            label="Utilisation %", zorder=3)
b2 = ax.bar([p + width / 2 for p in xpos], depot["workshop_pct"], width=width, color=SLATE,
            label="Workshop %", zorder=3)
vbar_labels(ax, b1, fmt="{:.0f}%")
vbar_labels(ax, b2, fmt="{:.0f}%")
ax.set_xticks(list(xpos))
ax.set_xticklabels(depot["depot"], rotation=12)
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
ax.set_ylim(0, max(depot["util_pct"]) * 1.22)
title(ax, "Depot Comparison: Utilisation vs Workshop %")
ax.legend(loc="upper right")
ax.grid(axis="y", color=GRID, linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(IMG / "depot_chart.png", facecolor="white")
plt.close()

print("Saved 4 polished chart images to", IMG)
