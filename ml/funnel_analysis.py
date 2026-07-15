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
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ml.chart_style import apply_style, NAVY, GREEN, GREEN_DARK, BLUE, SLATE, SLATE_LIGHT, RED, AMBER, GRID, DPI

RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "ml" / "reports"
IMG = ROOT / "docs" / "images"
apply_style()


def draw_funnel(ax, labels, values, colors, title_text, subtitle=None, value_fmt=lambda v: f"{v:,}"):
    """A true tapered funnel: each stage is a trapezoid whose width reflects
    its share of the top stage. Width uses a sqrt scale with a floor, so a
    funnel with a very steep drop-off (e.g. website visitors -> hires) still
    leaves every segment wide enough to hold its label - a linear scale would
    make the bottom stages too thin to read."""
    n = len(values)
    max_v = max(values)
    half_w = 8.6 / 2
    stage_h = 1.0
    gap = 0.06
    min_frac = 0.22  # narrowest a segment is ever allowed to get, as a fraction of half_w

    def frac(v):
        return max((v / max_v) ** 0.5, min_frac)

    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        top_y = n - i
        bot_y = top_y - stage_h + gap
        w_top = frac(values[i]) * half_w
        w_bot = (frac(values[i + 1]) if i < n - 1 else frac(values[i]) * 0.94) * half_w
        xs = [-w_top, w_top, w_bot, -w_bot]
        ys = [top_y, top_y, bot_y, bot_y]
        ax.fill(xs, ys, color=col, zorder=3)
        mid_y = (top_y + bot_y) / 2
        ax.text(0, mid_y + 0.11, lab, ha="center", va="center", fontsize=10, fontweight="bold",
                color="white", zorder=4)
        ax.text(0, mid_y - 0.16, value_fmt(val), ha="center", va="center", fontsize=12.5,
                fontweight="bold", color="white", zorder=4)
        if i > 0:
            conv = val / values[i - 1] * 100
            drop = 100 - conv
            note_color = GREEN_DARK if conv >= 90 else (AMBER if conv >= 70 else RED)
            ax.annotate(f"{conv:.0f}% carried through  ·  -{drop:.0f}%",
                        (half_w + 0.35, top_y), fontsize=8.6, color=note_color,
                        fontweight="bold", va="center", ha="left")
    ax.set_xlim(-half_w - 0.3, half_w + 3.6)
    ax.set_ylim(0.15, n + 0.85)
    ax.set_title(title_text, fontsize=13.5, fontweight="bold", color=NAVY, loc="left", pad=(20 if subtitle else 10))
    if subtitle:
        ax.text(-half_w - 0.3, n + 0.72, subtitle, fontsize=9, color=SLATE, va="bottom")
    ax.axis("off")


# =============================================================================
# 1) ORDER LIFECYCLE FUNNEL
# =============================================================================
orders = pd.read_csv(RAW / "hire_orders.csv")
STAGES = ["Quote Requested", "Quote Approved", "Dispatched", "On Hire", "Returned / Completed"]
stage_idx = {s: i for i, s in enumerate(STAGES)}
orders["reached_idx"] = orders["funnel_stage_reached"].map(stage_idx)
order_funnel_counts = [int((orders["reached_idx"] >= i).sum()) for i in range(len(STAGES))]

fig, ax = plt.subplots(figsize=(9.5, 7), dpi=DPI)
draw_funnel(ax, STAGES, order_funnel_counts, [GREEN, "#17B378", BLUE, "#4A9FE0", NAVY],
            "Order Lifecycle Funnel", subtitle=f"{order_funnel_counts[0]:,} quotes → completed hires, 12 months")
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

fig, ax = plt.subplots(figsize=(9, 5.4), dpi=DPI)
draw_funnel(ax, appr_stages, appr_counts, [AMBER, BLUE, GREEN],
            "Approvals Funnel", subtitle="Auction / parts / capital requests over £500, year to date")
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

fig, ax = plt.subplots(figsize=(9.5, 6), dpi=DPI)
draw_funnel(ax, dig_stages, dig_counts, [SLATE, BLUE, AMBER, GREEN],
            "Digital Marketing Funnel — ESTIMATED", subtitle="12-month total, directional only (see note below)")
fig.text(0.02, 0.015, "⚠ No real GA4/analytics data exists for cityhire.co.uk — this funnel is "
                       "directional, built from UK trade-services conversion benchmarks, not measured.",
         fontsize=8.5, color=RED, style="italic")
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
