"""
Product recommendation engine, two layers:

1. "Frequently hired together" — market-basket association rules (support,
   confidence, lift) over the category co-occurrence data, the standard
   metric for cross-sell recommendations (not just raw co-occurrence counts,
   which are biased toward popular categories).

2. "What to buy next" — a proactive stock-purchase recommendation that
   combines three signals already built: (a) categories about to enter their
   seasonal peak (seasonal_analysis.py), (b) categories currently below
   minimum stock (SQL query 6 / stock_below_minimum.csv), and (c) categories
   with strong ROI (roi_by_category.csv) — directly answering the project brief's
   "proactive recommendation for the purchase of stock" bullet.
"""
import json
from itertools import combinations
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "ml" / "reports"

# =============================================================================
# 1) MARKET BASKET ASSOCIATION RULES ("frequently hired together")
# =============================================================================
items = pd.read_csv(RAW / "hire_order_items.csv")
baskets = items.groupby("order_id")["category"].apply(lambda s: sorted(set(s)))
n_orders = len(baskets)

item_count = Counter()
pair_count = Counter()
for basket in baskets:
    for c in basket:
        item_count[c] += 1
    for a, b in combinations(basket, 2):
        pair_count[(a, b)] += 1
        pair_count[(b, a)] += 1  # symmetric, both directions needed for confidence(A->B) vs (B->A)

rules = []
for (a, b), co in pair_count.items():
    if co < 15:
        continue
    support = co / n_orders
    confidence = co / item_count[a]          # P(B|A)
    lift = confidence / (item_count[b] / n_orders)   # P(B|A) / P(B)
    rules.append({
        "antecedent": a, "consequent": b,
        "support": round(support, 4), "confidence": round(confidence, 4), "lift": round(lift, 3),
        "co_occurrences": co, "antecedent_orders": item_count[a],
    })

rules_df = pd.DataFrame(rules).sort_values("lift", ascending=False)
rules_df.to_csv(REPORTS / "association_rules.csv", index=False)

# top-3 recommendation per category, ranked by lift (min confidence filter to
# avoid recommending a category just because it's globally popular)
top_recs = (rules_df[rules_df["confidence"] >= 0.15]
            .sort_values(["antecedent", "lift"], ascending=[True, False])
            .groupby("antecedent").head(3))
top_recs.to_csv(REPORTS / "top_recommendations_by_category.csv", index=False)

print(f"Association rules: {len(rules_df)} pairs with >=15 co-occurrences")
print("\nTop 10 rules by lift:")
print(rules_df.head(10)[["antecedent", "consequent", "confidence", "lift"]].to_string(index=False))

# =============================================================================
# 2) PROACTIVE STOCK PURCHASE RECOMMENDATIONS
# =============================================================================
seasonal = pd.read_csv(REPORTS / "seasonal_recommendations.csv")
below_min = pd.read_csv(PROC / "stock_below_minimum.csv")
roi = pd.read_csv(PROC / "roi_by_category.csv")

# map project clusters back to their real categories for this join
CLUSTERS = {
    "Groundworks":     ["Plant", "Concreting & Compaction", "Site Equipment & Groundworks", "Survey & Location"],
    "Demolition":      ["Breakers & Drills", "Cutting & Grinding", "Safety, Ventilation & Extraction", "Propping & Support"],
    "Access & Height":  ["Powered Access", "Access", "Lifting Equipment"],
    "Site Setup":      ["Accommodation, Storage & Welfare", "Fencing & Barriers", "Power & Electrics", "Lighting"],
    "Finishing":       ["Painting & Decorating", "Sanding & Woodworking", "Cleaning"],
    "Logistics":       ["Material Handling & Logistics", "Lifting Equipment"],
    "Fixing":          ["Fixing & Fastening", "Mechanical & Electrical", "Breakers & Drills"],
    "Landscaping":     ["Landscaping & Gardening", "Fuel & Gas", "Climate Control"],
}
cluster_to_categories = {k: v for k, v in CLUSTERS.items()}

TODAY_MONTH = 7  # July 2026, matches TODAY in generate_dataset.py / generate_orders.py
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

purchase_recs = []
for _, row in seasonal.iterrows():
    peak_month_num = MONTHS.index(row["peak_month"]) + 1
    months_to_peak = (peak_month_num - TODAY_MONTH) % 12
    if months_to_peak > 4:
        continue  # only flag categories peaking within the next ~4 months
    cats_in_cluster = cluster_to_categories.get(row["category"], [])
    shortages = below_min[below_min["category"].isin(cats_in_cluster)]
    roi_rows = roi[roi["category"].isin(cats_in_cluster)]
    if len(shortages) == 0:
        continue
    avg_roi = roi_rows["est_roi_pct"].mean() if len(roi_rows) else None
    purchase_recs.append({
        "project_cluster": row["category"],
        "categories": ", ".join(cats_in_cluster),
        "seasonal_peak": row["peak_month"],
        "months_to_peak": int(months_to_peak),
        "depots_currently_short": int(shortages["depot"].nunique()),
        "shortage_combos": int(len(shortages)),
        "avg_category_roi_pct": round(float(avg_roi), 1) if avg_roi else None,
        "recommendation": (
            f"{row['category']} categories are already short of minimum stock at "
            f"{shortages['depot'].nunique()} depot(s) and enter their seasonal peak in "
            f"{row['peak_month']} ({months_to_peak} month(s) away) — purchase ahead of the peak, "
            f"not during it."
        ),
    })

purchase_recs = sorted(purchase_recs, key=lambda r: r["months_to_peak"])
(REPORTS / "stock_purchase_recommendations.json").write_text(
    json.dumps(purchase_recs, indent=2), encoding="utf-8")
pd.DataFrame(purchase_recs).to_csv(REPORTS / "stock_purchase_recommendations.csv", index=False)

print(f"\nProactive stock purchase recommendations: {len(purchase_recs)}")
for r in purchase_recs:
    print(f"  {r['project_cluster']}: peak in {r['months_to_peak']}mo, "
          f"{r['depots_currently_short']} depots short, ROI {r['avg_category_roi_pct']}%")
