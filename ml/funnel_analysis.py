"""
Three funnels:
1. Order lifecycle funnel - from the synthetic hire_orders dataset (real
   stage-by-stage drop-off, not just a final-status count).
2. Approvals funnel - request -> review -> approved/rejected, from the
   original approvals.csv (job-spec data, not the new orders dataset).
3. Digital marketing funnel - visitors -> product views -> quote requests ->
   confirmed hires. NOTE: City Hire has no public GA4/analytics data
   available, so this funnel is directional/estimated from UK trade-services
   conversion-rate benchmarks (see docs/CityHire_Competitor_Marketing_Intelligence.docx),
   not measured. Flagged clearly wherever it's used.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "ml" / "reports"
IMG = ROOT / "docs" / "images"

NAVY, GREEN, BLUE, SLATE, RED, AMBER = "#0C1114", "#009B66", "#2A7ACC", "#3C5667", "#C0392B", "#D98E04"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "text.color": NAVY, "figure.facecolor": "white", "axes.facecolor": "white",
})


def draw_funnel(ax, labels, values, colors, title, value_fmt=lambda v: f"{v:,}"):
    n = len(values)
    max_v = max(values)
    bar_h = 0.62
    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        y = n - i
        w = (val / max_v) * 8.5
        x0 = (8.5 - w) / 2
        ax.barh(y, w, left=x0, height=bar_h, color=col, edgecolor="white", linewidth=1.2, zorder=3)
        ax.text(4.25, y, f"{lab}\n{value_fmt(val)}", ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="white", zorder=4)
        if i > 0:
            conv = val / values[i - 1] * 100
            ax.text(8.9, y + 0.5, f"{conv:.0f}%\nof prev.", ha="left", va="center",
                    fontsize=8, color=SLATE)
    ax.set_xlim(-0.3, 10.5)
    ax.set_ylim(0.2, n + 0.8)
    ax.set_title(title, fontsize=12.5, fontweight="bold", color=NAVY, loc="left", pad=10)
    ax.axis("off")


# =============================================================================
# 1) ORDER LIFECYCLE FUNNEL
# =============================================================================
orders = pd.read_csv(RAW / "hire_orders.csv")
STAGES = ["Quote Requested", "Quote Approved", "Dispatched", "On Hire", "Returned / Completed"]
stage_idx = {s: i for i, s in enumerate(STAGES)}
orders["reached_idx"] = orders["funnel_stage_reached"].map(stage_idx)
order_funnel_counts = [int((orders["reached_idx"] >= i).sum()) for i in range(len(STAGES))]

fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
draw_funnel(ax, STAGES, order_funnel_counts, [GREEN, GREEN, BLUE, BLUE, NAVY],
            f"Order Lifecycle Funnel ({order_funnel_counts[0]:,} quotes → completed hires, 12 months)")
plt.tight_layout()
plt.savefig(IMG / "order_funnel.png", facecolor="white")
plt.close()

# =============================================================================
# 2) APPROVALS FUNNEL (by outcome)
# =============================================================================
approvals = pd.read_csv(RAW / "approvals.csv")
total = len(approvals)
approved = int((approvals["status"] == "Approved").sum())
pending = int((approvals["status"] == "Pending").sum())
rejected = int((approvals["status"] == "Rejected").sum())
appr_stages = ["Requested (>£500)", "Reviewed", "Approved"]
appr_counts = [total, total - rejected, approved]

fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=200)
draw_funnel(ax, appr_stages, appr_counts, [AMBER, BLUE, GREEN],
            "Approvals Funnel (Auction / Parts / Capital Requests, YTD)")
plt.tight_layout()
plt.savefig(IMG / "approvals_funnel.png", facecolor="white")
plt.close()

# =============================================================================
# 3) DIGITAL MARKETING FUNNEL (estimated/benchmarked)
# =============================================================================
digital = pd.read_csv(RAW / "digital_funnel_monthly.csv")
totals = digital[["visitors", "product_views", "quote_requests", "confirmed_hires"]].sum()
dig_stages = ["Website Visitors", "Product Page Views", "Quote Requests", "Confirmed Hires"]
dig_counts = [int(totals["visitors"]), int(totals["product_views"]),
              int(totals["quote_requests"]), int(totals["confirmed_hires"])]

fig, ax = plt.subplots(figsize=(8, 5.2), dpi=200)
draw_funnel(ax, dig_stages, dig_counts, [SLATE, BLUE, AMBER, GREEN],
            "Digital Marketing Funnel — ESTIMATED (12-month total)")
fig.text(0.02, 0.02, "No real GA4/analytics data exists for cityhire.co.uk — this funnel is "
                       "directional, built from UK trade-services conversion benchmarks, not measured.",
         fontsize=8, color=RED, style="italic")
plt.tight_layout(rect=(0, 0.05, 1, 1))
plt.savefig(IMG / "digital_funnel.png", facecolor="white")
plt.close()

# =============================================================================
# Summary
# =============================================================================
summary = {
    "order_funnel": dict(zip(STAGES, order_funnel_counts)),
    "order_funnel_overall_conversion_pct": round(order_funnel_counts[-1] / order_funnel_counts[0] * 100, 1),
    "approvals_funnel": dict(zip(appr_stages, appr_counts)),
    "approvals_approval_rate_pct": round(approved / total * 100, 1),
    "digital_funnel_estimated": dict(zip(dig_stages, dig_counts)),
    "digital_funnel_overall_conversion_pct_estimated": round(dig_counts[-1] / dig_counts[0] * 100, 2),
}
(REPORTS / "funnel_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nSaved: order_funnel.png, approvals_funnel.png, digital_funnel.png in {IMG}")
