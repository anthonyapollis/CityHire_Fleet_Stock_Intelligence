"""Execute the analysis_queries.sql statements and export each result set to CSV
for use in the Excel workbook and the HTML dashboard."""
import sqlite3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "cityhire_fleet.db"
SQL_FILE = ROOT / "sql" / "analysis_queries.sql"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    "workshop_inservice_by_month_depot",
    "workshop_pct_fleet_trend",
    "utilisation_by_category_90d",
    "depots_below_utilisation_target",
    "capex_vs_budget_by_category",
    "months_over_budget",
    "daily_stock_stats_latest",
    "fleeting_transfers_summary",
    "unfulfilled_transfers",
    "stock_below_minimum",
    "pending_approvals_over_500",
    "approvals_summary_by_type",
    "external_repairs_by_supplier",
    "repairs_pending_approval",
    "roi_by_category",
    "lowest_roi_assets",
    "undersupplied_categories",
]

sql_text = SQL_FILE.read_text(encoding="utf-8")
# strip line comments first so a ";" inside a comment can't fake a statement break
code_only = "\n".join(line.split("--", 1)[0] for line in sql_text.splitlines())
raw_statements = [s.strip() for s in code_only.split(";") if s.strip()]
statements = [s for s in raw_statements if re.search(r"\bselect\b", s, re.IGNORECASE)]

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

assert len(statements) == len(NAMES), f"{len(statements)} statements vs {len(NAMES)} names — keep in sync"

for name, stmt in zip(NAMES, statements):
    cur.execute(stmt)
    rows = cur.fetchall()
    if not rows:
        print(f"{name}: 0 rows")
        continue
    cols = rows[0].keys()
    path = OUT / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    print(f"{name}: {len(rows)} rows -> {path.name}")

conn.close()
