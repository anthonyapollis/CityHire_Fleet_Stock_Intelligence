"""
Synthetic hire-orders dataset - the foundation for graph, funnel, and
recommendation analysis. Not part of the original job-spec dataset; built to
support "customers who hire X also hire Y" (market basket / graph analysis),
order lifecycle funnels, and seasonal demand patterns.

Category baskets are drawn from realistic construction "project type"
clusters (not pure random pairs) so there is genuine co-occurrence signal
for graph/association analysis - the same principle used for the capex
overspend and workshop-improvement signal in generate_dataset.py.
"""
import random
import csv
from datetime import date, timedelta
from pathlib import Path

random.seed(7)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TODAY = date(2026, 7, 15)
HISTORY_DAYS = 365

# Project-type clusters: categories that genuinely get hired together on a
# real construction site. Each order draws mostly from one cluster plus a
# small chance of a cross-cluster add-on (noise).
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
ALL_CATEGORIES = sorted({c for cats in CLUSTERS.values() for c in cats})

# Seasonal weight per cluster (project types that peak in different seasons)
CLUSTER_SEASONALITY = {
    "Groundworks": {4: 1.3, 5: 1.4, 6: 1.4, 7: 1.3, 8: 1.2, 9: 1.1},
    "Landscaping": {3: 1.5, 4: 1.7, 5: 1.8, 6: 1.6, 7: 1.4, 8: 1.2},
    "Site Setup": {1: 1.2, 11: 1.2, 12: 1.1},
    "Demolition": {},   # roughly flat year-round
    "Access & Height": {5: 1.2, 6: 1.3, 7: 1.3, 8: 1.2},
    "Finishing": {9: 1.2, 10: 1.3, 11: 1.2},
    "Logistics": {},
    "Fixing": {},
}

SITES = [f"Site-{i:03d}" for i in range(1, 181)]
CUSTOMER_TYPES = ["Main Contractor", "Groundworks Sub-contractor", "Demolition Specialist",
                   "M&E Contractor", "Landscaping Contractor", "Facilities Management", "Self-Employed Trade"]

# Order funnel stages, with realistic drop-off at each gate
FUNNEL_STAGES = ["Quote Requested", "Quote Approved", "Dispatched", "On Hire", "Returned / Completed"]
STAGE_DROPOFF = {"Quote Requested": 0.0, "Quote Approved": 0.14, "Dispatched": 0.06,
                  "On Hire": 0.03, "Returned / Completed": 0.02}


def month_weight(cluster, month):
    return CLUSTER_SEASONALITY.get(cluster, {}).get(month, 1.0)


def gen_orders(n_orders=5000):
    orders = []
    order_items = []
    order_id = 6000
    for _ in range(n_orders):
        offset = random.randint(0, HISTORY_DAYS)
        order_date = TODAY - timedelta(days=offset)
        cluster = random.choices(
            list(CLUSTERS.keys()),
            weights=[month_weight(c, order_date.month) for c in CLUSTERS.keys()],
        )[0]
        basket_size = random.choices([1, 2, 3, 4], weights=[15, 40, 30, 15])[0]
        cats = list(CLUSTERS[cluster])
        random.shuffle(cats)
        basket = cats[:min(basket_size, len(cats))]
        # small chance of a cross-cluster add-on item (realistic noise)
        if random.random() < 0.18:
            extra = random.choice(ALL_CATEGORIES)
            if extra not in basket:
                basket.append(extra)

        # simulate funnel progression with drop-off
        reached_stage = FUNNEL_STAGES[-1]
        for stage in FUNNEL_STAGES[1:]:
            if random.random() < STAGE_DROPOFF[stage]:
                reached_stage = FUNNEL_STAGES[FUNNEL_STAGES.index(stage) - 1]
                break

        order_id += 1
        site = random.choice(SITES)
        cust_type = random.choice(CUSTOMER_TYPES)
        order_value = round(sum(random.uniform(180, 2200) for _ in basket), 2)

        orders.append({
            "order_id": f"ORD-{order_id}",
            "site": site,
            "customer_type": cust_type,
            "order_date": order_date.isoformat(),
            "project_cluster": cluster,
            "basket_size": len(basket),
            "order_value_gbp": order_value,
            "funnel_stage_reached": reached_stage,
        })
        for cat in basket:
            order_items.append({"order_id": f"ORD-{order_id}", "category": cat})

    return orders, order_items


def gen_digital_funnel():
    """Benchmarked, directional digital-marketing funnel (no real GA4 data for
    City Hire exists, so this is estimated from public UK trade-services
    conversion-rate benchmarks, clearly flagged as such)."""
    monthly = []
    d = date(TODAY.year - 1, TODAY.month, 1)
    months = []
    while d <= TODAY.replace(day=1):
        months.append(d)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    for m in months:
        seasonal = 1.25 if m.month in (4, 5, 6, 7, 8, 9) else 0.85
        visitors = int(random.uniform(9000, 13000) * seasonal)
        product_views = int(visitors * random.uniform(0.42, 0.52))
        quote_requests = int(product_views * random.uniform(0.07, 0.11))
        confirmed_hires = int(quote_requests * random.uniform(0.38, 0.48))
        monthly.append({
            "month": m.isoformat(), "visitors": visitors, "product_views": product_views,
            "quote_requests": quote_requests, "confirmed_hires": confirmed_hires,
        })
    return monthly


if __name__ == "__main__":
    orders, order_items = gen_orders()
    digital_funnel = gen_digital_funnel()

    def write_csv(name, rows):
        path = RAW / f"{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {path} ({len(rows)} rows)")

    write_csv("hire_orders", orders)
    write_csv("hire_order_items", order_items)
    write_csv("digital_funnel_monthly", digital_funnel)

    from collections import Counter
    stage_counts = Counter(o["funnel_stage_reached"] for o in orders)
    print("Order funnel reached-stage counts:", dict(stage_counts))
