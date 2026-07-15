"""Generate the chart images used in the CityHire ebook, in City Hire's brand colors."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
IMG = ROOT / "docs" / "images"
IMG.mkdir(parents=True, exist_ok=True)

NAVY = "#0C1114"
GREEN = "#009B66"
BLUE = "#2A7ACC"
SLATE = "#3C5667"
LIGHT = "#F2F5F7"
RED = "#C0392B"
AMBER = "#D98E04"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "axes.edgecolor": "#C3CDD3",
    "axes.labelcolor": SLATE,
    "text.color": NAVY,
    "xtick.color": SLATE,
    "ytick.color": SLATE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

# =============================================================================
# 1) Workshop % / In-service trend
# =============================================================================
trend = pd.read_csv(PROC / "monthly_fleet_trend.csv")
fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200)
x = range(len(trend))
ax.plot(x, trend["utilisation_pct"], color=GREEN, linewidth=2.5, marker="o", markersize=5, label="Utilisation %")
in_service = 100 - trend["workshop_pct"]
ax.plot(x, in_service, color=BLUE, linewidth=2.5, marker="o", markersize=5, label="In-Service %")
ax.axhline(60, color=RED, linestyle="--", linewidth=1, alpha=0.6)
ax.axhline(85, color=RED, linestyle="--", linewidth=1, alpha=0.6)
ax.set_xticks(list(x))
ax.set_xticklabels([m[2:] for m in trend["month"]], fontsize=8.5)
ax.set_ylim(0, 105)
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
ax.set_title("12-Month Trend: Utilisation vs In-Service %", fontsize=12, fontweight="bold", color=NAVY, loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.grid(axis="y", color="#E1E6EA", linewidth=0.8)
plt.tight_layout()
plt.savefig(IMG / "trend_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 2) Capex variance by category (top 10 by absolute variance)
# =============================================================================
capex = pd.read_csv(PROC / "capex_vs_budget_by_category.csv")
capex = capex.reindex(capex["ytd_variance_gbp"].abs().sort_values(ascending=False).index).head(10)
capex = capex.sort_values("ytd_variance_gbp")
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
colors = [RED if v > 0 else GREEN for v in capex["ytd_variance_gbp"]]
ax.barh(capex["category"], capex["ytd_variance_gbp"] / 1000, color=colors, height=0.6)
ax.axvline(0, color=SLATE, linewidth=1)
ax.set_xlabel("YTD Variance (£000s, actual - budget)", fontsize=9)
ax.set_title("Capex Variance — Top 10 Categories by Magnitude", fontsize=12, fontweight="bold", color=NAVY, loc="left")
ax.grid(axis="x", color="#E1E6EA", linewidth=0.8)
plt.tight_layout()
plt.savefig(IMG / "capex_variance_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 3) ROI leaderboard
# =============================================================================
roi = pd.read_csv(PROC / "roi_by_category.csv").sort_values("est_roi_pct", ascending=True).tail(10)
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
ax.barh(roi["category"], roi["est_roi_pct"], color=GREEN, height=0.6)
ax.set_xlabel("Estimated annual ROI (%)", fontsize=9)
ax.set_title("Top 10 Categories by Estimated ROI", fontsize=12, fontweight="bold", color=NAVY, loc="left")
ax.grid(axis="x", color="#E1E6EA", linewidth=0.8)
plt.tight_layout()
plt.savefig(IMG / "roi_chart.png", facecolor="white")
plt.close()

# =============================================================================
# 4) Depot comparison (utilisation vs workshop)
# =============================================================================
depot = pd.read_csv(PROC / "depot_summary.csv").sort_values("util_pct", ascending=False)
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200)
width = 0.38
xpos = range(len(depot))
ax.bar([p - width/2 for p in xpos], depot["util_pct"], width=width, color=GREEN, label="Utilisation %")
ax.bar([p + width/2 for p in xpos], depot["workshop_pct"], width=width, color=SLATE, label="Workshop %")
ax.set_xticks(list(xpos))
ax.set_xticklabels(depot["depot"], fontsize=8.5, rotation=15)
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
ax.set_title("Depot Comparison: Utilisation vs Workshop %", fontsize=12, fontweight="bold", color=NAVY, loc="left")
ax.legend(frameon=False, fontsize=9)
ax.grid(axis="y", color="#E1E6EA", linewidth=0.8)
plt.tight_layout()
plt.savefig(IMG / "depot_chart.png", facecolor="white")
plt.close()

print("Saved 4 chart images to", IMG)
