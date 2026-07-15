"""
Load the CityHire fleet data into a real Azure Database for PostgreSQL
(Flexible Server) and run analytical queries against it - genuine cloud DB
usage, not a local stand-in. Captures proof (row counts + query results) to
ml/reports/azure_postgres_proof.json before the server gets torn down.
"""
import json
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "ml" / "reports"

HOST = "cityhire-pg-temp.postgres.database.azure.com"
DB = "postgres"
USER = "cityhireadmin"
PASSWORD = "TempP@ssw0rd2026!"

conn = psycopg2.connect(host=HOST, dbname=DB, user=USER, password=PASSWORD, sslmode="require")
cur = conn.cursor()

print("Connected to Azure Database for PostgreSQL:", HOST)

# =============================================================================
# Load stock_master
# =============================================================================
sm = pd.read_csv(RAW / "stock_master.csv")
cur.execute("DROP TABLE IF EXISTS stock_master")
cur.execute("""
    CREATE TABLE stock_master (
        stock_code TEXT, category TEXT, subcategory TEXT, product_name TEXT,
        brand TEXT, depot TEXT, purchase_date DATE, capex_gbp NUMERIC,
        book_value_gbp NUMERIC, age_years NUMERIC, condition TEXT, status TEXT,
        utilisation_pct_ytd NUMERIC, day_rate_gbp NUMERIC, last_service_date DATE,
        next_service_due DATE, min_stock_level INT, current_units_at_depot INT
    )
""")
cols = list(sm.columns)
rows = [tuple(r) for r in sm[cols].itertuples(index=False, name=None)]
execute_values(cur, f"INSERT INTO stock_master ({','.join(cols)}) VALUES %s", rows)
conn.commit()
print(f"Loaded stock_master: {len(rows)} rows")

# =============================================================================
# Load daily_stock_stats
# =============================================================================
daily = pd.read_csv(RAW / "daily_stock_stats.csv")
cur.execute("DROP TABLE IF EXISTS daily_stock_stats")
cur.execute("""
    CREATE TABLE daily_stock_stats (
        date DATE, depot TEXT, category TEXT, fleet_units INT, units_on_hire INT,
        units_in_workshop INT, units_available INT, utilisation_pct NUMERIC, workshop_pct NUMERIC
    )
""")
cols2 = list(daily.columns)
rows2 = [tuple(r) for r in daily[cols2].itertuples(index=False, name=None)]
execute_values(cur, f"INSERT INTO daily_stock_stats ({','.join(cols2)}) VALUES %s", rows2, page_size=2000)
conn.commit()
print(f"Loaded daily_stock_stats: {len(rows2)} rows")

# =============================================================================
# Run real analytical queries against the cloud DB
# =============================================================================
proof = {"host": HOST, "tables_loaded": {"stock_master": len(rows), "daily_stock_stats": len(rows2)}}

cur.execute("""
    SELECT category, COUNT(*) AS units, ROUND(SUM(capex_gbp), 2) AS total_capex,
           ROUND(AVG(utilisation_pct_ytd), 1) AS avg_util,
           ROUND(SUM(day_rate_gbp * utilisation_pct_ytd / 100.0 * 365), 2) AS est_revenue
    FROM stock_master
    GROUP BY category
    ORDER BY est_revenue DESC
    LIMIT 5
""")
proof["top5_categories_by_revenue"] = [
    {"category": r[0], "units": r[1], "total_capex": float(r[2]), "avg_util": float(r[3]), "est_revenue": float(r[4])}
    for r in cur.fetchall()
]

cur.execute("""
    SELECT depot, ROUND(AVG(utilisation_pct), 1) AS avg_util, ROUND(AVG(workshop_pct), 1) AS avg_workshop
    FROM daily_stock_stats
    WHERE date >= (SELECT MAX(date) FROM daily_stock_stats) - INTERVAL '90 days'
    GROUP BY depot
    ORDER BY avg_util DESC
""")
proof["depot_util_last_90d"] = [
    {"depot": r[0], "avg_util": float(r[1]), "avg_workshop": float(r[2])} for r in cur.fetchall()
]

cur.execute("SELECT COUNT(*) FROM stock_master WHERE status = 'Auction Pending'")
proof["auction_pending_count"] = cur.fetchone()[0]

cur.execute("SELECT version()")
proof["postgres_version"] = cur.fetchone()[0]

(REPORTS / "azure_postgres_proof.json").write_text(json.dumps(proof, indent=2, default=str), encoding="utf-8")
print("\nSaved proof to ml/reports/azure_postgres_proof.json")
print(json.dumps(proof, indent=2, default=str))

cur.close()
conn.close()
