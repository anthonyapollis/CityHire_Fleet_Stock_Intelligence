# CityHire Fleet & Stock Intelligence

A full-stack applied data & automation platform: SQL, Excel, Power BI, a live Azure database,
an interactive dashboard and depot map, graph/network analysis, funnel tracking, seasonal
forecasting, local ML, and a market-basket recommendation engine — nine layers, all reading
from one consistent 1,612-asset fleet.

> **Data grounding:** category structure and 220+ real product/model names (e.g. "Nifty Lift
> HR21 20.8m Hybrid Boom Lift", "Hilti TE 3000-AVR Heavy Breaker") plus a handful of real
> product photos were extracted from the public product catalogue at
> [cityhire.co.uk](https://cityhire.co.uk) on 2026-07-15.
>
> **Everything else — fleet quantities, stock codes, costs, dates, utilisation, repairs,
> approvals, orders, transfers — is SYNTHETIC**, generated for this demonstration. This is not
> City Hire's real operational or financial data.

## The ebook

**[`docs/CityHire_Fleet_Intelligence_Ebook.docx`](docs/CityHire_Fleet_Intelligence_Ebook.docx)**
(+ PDF) is the single consolidated deliverable — the full story, every chart, every finding,
in one document.

## What's here

| Folder | Contents |
|---|---|
| `data/raw/` | Synthetic source CSVs — stock master, daily stats, repairs, approvals, capex, transfers, sale codes, hire orders/basket items, digital funnel |
| `data/processed/` | SQLite DB, SQL query result exports, depot/flow summaries |
| `sql/` | `analysis_queries.sql` — 17 queries mapped to the project brief's success points and daily tasks |
| `excel/` | 10-sheet workbook, every KPI a live formula (SUMIFS/AVERAGEIFS/COUNTIFS/SUMPRODUCT) |
| `dashboard/` | Self-contained interactive HTML dashboard (KPI tiles, trend/variance charts, ROI leaderboard, action-queue tables) |
| `ml/` | Local scikit-learn models, seasonal decomposition, graph analysis (NetworkX), funnel analysis, recommendation engine, and the Azure PostgreSQL scripts |
| `docs/` | The consolidated ebook (docx + PDF) and all chart/product images |
| `scripts/` | Generator/build scripts — re-run any of them to regenerate that deliverable |

## The Power BI model

Built live in Power BI Desktop via the Tabular Object Model API: 11 tables (7 fact tables +
Calendar/Category/Depot dimensions), 18 relationships, 21 DAX measures across 9 display
folders matching the project brief's structure. Not included in this repo (`.pbix` lives locally).

## The live Azure database

`ml/azure/` provisioned a real Azure Database for PostgreSQL (Flexible Server), loaded 55,414
rows across two tables, and ran live analytical queries against it — then tore the resource
group down immediately after capturing results. See the ebook for the full story, including
which Azure resource types this trial subscription's cost-control policy blocks (ML
workspaces, Databricks, Azure SQL Server, VMs, Cosmos DB) and why PostgreSQL Flexible Server
was the one that worked.

## Reproducing the build

```bash
pip install pandas openpyxl scikit-learn joblib python-docx matplotlib statsmodels networkx psycopg2-binary

python scripts/generate_dataset.py       # synthetic fleet dataset + SQLite DB
python scripts/generate_orders.py        # synthetic hire-orders dataset (graph/funnel/recs)
python scripts/run_sql_report.py         # run all 17 SQL queries, export results
python scripts/build_excel_report.py     # Excel workbook (then recalc in Excel)

python ml/train_models.py                # local ML models
python ml/seasonal_analysis.py           # seasonal decomposition + demand index
python ml/graph_analysis.py              # category co-occurrence + depot network graphs
python ml/funnel_analysis.py             # order/approvals/digital funnels
python ml/recommendations.py             # association rules + stock purchase recs

python scripts/build_ebook_charts.py     # polished chart images
python scripts/build_final_ebook.py      # the consolidated ebook
```

## Why local ML instead of Azure Databricks/ML

The Azure trial used for other projects in this portfolio was within days of expiring when
this build started, and a subscription-level policy blocks Azure ML workspaces and Databricks
outright. The ML layer (`ml/train_models.py`) runs entirely on local scikit-learn instead,
with the same modeling rigor (train/test splits, honest metrics, feature importance) — see
`ml/azure/` for what genuinely does run on Azure (PostgreSQL).

---
Built by Anthony Apollis — anthony.apollis@gmail.com
