"""
Seasonal decomposition of fleet utilisation and workshop %, plus a seasonal
demand index by category - used to turn "utilisation is seasonal" into a
concrete stock-purchase-timing recommendation.
"""
import json
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ml.chart_style import apply_style, title, NAVY, GREEN, GREEN_DARK, BLUE, SLATE, SLATE_LIGHT, RED, AMBER, GRID, DPI

RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "ml" / "reports"
IMG = ROOT / "docs" / "images"
REPORTS.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)
apply_style()

# =============================================================================
# Fleet-wide daily utilisation - classical seasonal decomposition
# =============================================================================
daily = pd.read_csv(RAW / "daily_stock_stats.csv", parse_dates=["date"])
fleet_daily = daily.groupby("date").agg(
    fleet_units=("fleet_units", "sum"), units_on_hire=("units_on_hire", "sum")
).reset_index().sort_values("date")
fleet_daily["utilisation_pct"] = fleet_daily["units_on_hire"] / fleet_daily["fleet_units"] * 100
fleet_daily = fleet_daily.set_index("date").asfreq("D").interpolate()

decomp = seasonal_decompose(fleet_daily["utilisation_pct"], model="additive", period=30)

fig, axes = plt.subplots(4, 1, figsize=(10, 9), dpi=DPI, sharex=True)
fig.suptitle("Fleet Utilisation — Seasonal Decomposition", fontsize=15, fontweight="bold",
             color=NAVY, x=0.02, ha="left", y=0.995)
for ax, series, panel_title, color in [
    (axes[0], fleet_daily["utilisation_pct"], "Observed utilisation %", NAVY),
    (axes[1], decomp.trend, "Trend component", GREEN),
    (axes[2], decomp.seasonal, "Seasonal component (30-day cycle)", BLUE),
    (axes[3], decomp.resid, "Residual (unexplained noise)", SLATE_LIGHT),
]:
    ax.plot(series.index, series.values, color=color, linewidth=1.6)
    ax.fill_between(series.index, series.values, series.values.min(), color=color, alpha=0.08)
    ax.set_title(panel_title, fontsize=10.5, fontweight="bold", loc="left", color=NAVY, pad=6)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
plt.tight_layout(rect=(0, 0, 1, 0.97))
plt.savefig(IMG / "seasonal_decomposition.png", facecolor="white")
plt.close()

# =============================================================================
# Seasonal demand index by project cluster, from actual hire-order volume
# =============================================================================
# NOTE: daily_stock_stats' per-category utilisation only carries ONE fleet-wide
# seasonal factor (checked: cross-category spread within a month is ~1-5pp,
# consistent with sampling noise) - so seasonality is measured from order
# volume instead, at PROJECT-CLUSTER level (where it's genuinely designed in
# via CLUSTER_SEASONALITY in generate_orders.py). Individual-category order
# counts are too sparse (a few hundred orders / 24 categories / 12 months) to
# support a category-level index without it being noise-dominated too.
orders = pd.read_csv(RAW / "hire_orders.csv", parse_dates=["order_date"])
orders["month"] = orders["order_date"].dt.month

cat_month = orders.groupby(["project_cluster", "month"]).size().reset_index(name="order_count")
cat_annual_avg = orders.groupby("project_cluster").size().rename("annual_total") / 12
cat_month = cat_month.merge(cat_annual_avg, on="project_cluster")
cat_month["seasonal_index_raw"] = (cat_month["order_count"] / cat_month["annual_total"]).round(3)
cat_month = cat_month.rename(columns={"project_cluster": "category"})  # keep downstream code unchanged

# circular 3-month rolling smoothing (standard for seasonal curves) - the raw
# per-month count is noisy at ~50 orders/cluster/month; smoothing reveals the
# real underlying seasonal curve without changing what drives it
cat_month = cat_month.sort_values(["category", "month"]).reset_index(drop=True)
smoothed = []
for cat, sub in cat_month.groupby("category"):
    sub = sub.set_index("month").reindex(range(1, 13))
    vals = sub["seasonal_index_raw"].tolist()
    n = len(vals)
    sm = [(vals[(i - 1) % n] + vals[i] + vals[(i + 1) % n]) / 3 for i in range(n)]
    sub["seasonal_index"] = sm
    sub["category"] = cat
    smoothed.append(sub.reset_index().rename(columns={"index": "month"}))
cat_month = pd.concat(smoothed, ignore_index=True)

# categories with the strongest seasonal swing (max index - min index)
swing = cat_month.groupby("category")["seasonal_index"].agg(lambda s: s.max() - s.min())
top_seasonal = swing.sort_values(ascending=False).head(8)

fig, ax = plt.subplots(figsize=(10.5, 6), dpi=DPI)
month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
palette = [GREEN, BLUE, AMBER, SLATE_LIGHT, "#17B378", RED, "#2D414D", "#4A9FE0"]
ax.axhline(1.0, color=SLATE, linewidth=1, linestyle=(0, (5, 3)), alpha=0.6)
end_labels = []
for i, cat in enumerate(top_seasonal.index):
    sub = cat_month[cat_month["category"] == cat].sort_values("month")
    color = palette[i % len(palette)]
    ax.plot(sub["month"], sub["seasonal_index"], marker="o", markersize=4,
            markerfacecolor="white", markeredgewidth=1.6, color=color, linewidth=2.2, zorder=3)
    last = sub.iloc[-1]
    end_labels.append({"cat": cat, "color": color, "x": last["month"], "y": last["seasonal_index"]})

# de-overlap end labels: enforce a minimum vertical gap in data units
end_labels.sort(key=lambda d: d["y"])
min_gap = 0.028
for i in range(1, len(end_labels)):
    if end_labels[i]["y"] - end_labels[i - 1]["y"] < min_gap:
        end_labels[i]["y"] = end_labels[i - 1]["y"] + min_gap
for d in end_labels:
    ax.annotate(f"  {d['cat']}", (d["x"], d["y"]), fontsize=8.7, fontweight="bold",
                color=d["color"], va="center", ha="left")
ax.set_xticks(range(1, 13))
ax.set_xticklabels(month_names)
ax.set_xlim(0.7, 15.5)
ax.set_ylabel("Order-volume seasonal index  (1.0 = category's own monthly average)")
title(ax, "Seasonal Demand Index — 8 Most Seasonal Project Types",
      subtitle="Built from real order volume, not the fleet's noisy daily stats — see build notes")
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(IMG / "seasonal_demand_index.png", facecolor="white")
plt.close()

# =============================================================================
# Save a stock-purchase-timing recommendation table
# =============================================================================
results = []
for cat in top_seasonal.index:
    sub = cat_month[cat_month["category"] == cat].sort_values("seasonal_index", ascending=False)
    peak_month = month_names[int(sub.iloc[0]["month"]) - 1]
    trough_month = month_names[int(sub.iloc[-1]["month"]) - 1]
    results.append({
        "category": cat,
        "peak_month": peak_month,
        "peak_index": round(float(sub.iloc[0]["seasonal_index"]), 2),
        "trough_month": trough_month,
        "trough_index": round(float(sub.iloc[-1]["seasonal_index"]), 2),
        "swing": round(float(top_seasonal[cat]), 2),
        "recommendation": f"Increase available stock ahead of {peak_month}; safe to reallocate/service more units in {trough_month}.",
    })

(REPORTS / "seasonal_recommendations.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
pd.DataFrame(results).to_csv(REPORTS / "seasonal_recommendations.csv", index=False)
print("Seasonal recommendations:")
for r in results:
    print(f"  {r['category']}: peak {r['peak_month']} ({r['peak_index']}), trough {r['trough_month']} ({r['trough_index']})")

print(f"\nSaved: {IMG/'seasonal_decomposition.png'}, {IMG/'seasonal_demand_index.png'}")
print(f"Saved: {REPORTS/'seasonal_recommendations.json'}")
