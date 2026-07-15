# CityHire Fleet & Stock Intelligence

A portfolio build for a **Data & Automation Analyst** application (plant/tool hire sector),
built end-to-end: SQL, Excel, Power BI, an interactive dashboard, an interactive depot map,
local ML models, and competitor/marketing intelligence — all from one consistent dataset.

> **Data grounding:** category structure and 220+ real product/model names (e.g. "Nifty Lift
> HR21 20.8m Hybrid Boom Lift", "Hilti TE 3000-AVR Heavy Breaker") were extracted from the
> public product catalogue at [cityhire.co.uk](https://cityhire.co.uk) on 2026-07-15.
>
> **Everything else — fleet quantities, stock codes, costs, dates, utilisation, repairs,
> approvals, transfers — is SYNTHETIC**, generated for this demonstration. This is not
> City Hire's real operational or financial data.

## What's here

| Folder | Contents |
|---|---|
| `data/raw/` | Synthetic source CSVs — stock master, daily stats, repairs, approvals, capex, transfers, sale codes |
| `data/processed/` | SQLite DB, SQL query result exports, depot/flow summaries |
| `sql/` | `analysis_queries.sql` — 17 queries mapped to the job spec's success points and daily tasks |
| `excel/` | 10-sheet workbook, every KPI a live formula (SUMIFS/AVERAGEIFS/COUNTIFS/SUMPRODUCT) |
| `dashboard/` | Self-contained interactive HTML dashboard (KPI tiles, trend/variance charts, ROI leaderboard, action-queue tables) |
| `ml/` | Local scikit-learn models (utilisation/workshop forecasting, capex-overspend classifier, day-rate pricing) — no cloud infra used |
| `docs/` | Case study, competitor & marketing intelligence, and the full data-story ebook (docx + PDF) |
| `scripts/` | All generator/build scripts — re-run any of them to regenerate that deliverable |

## The Power BI model

Built live in Power BI Desktop via the Tabular Object Model API: 11 tables (7 fact tables +
Calendar/Category/Depot dimensions), 18 relationships, 21 DAX measures across 9 display
folders matching the job spec's structure. Not included in this repo (`.pbix` lives locally) —
see `docs/CityHire_Data_Story.docx` for the full writeup.

## Reproducing the build

```bash
pip install pandas openpyxl scikit-learn joblib python-docx matplotlib
python scripts/generate_dataset.py       # synthetic dataset + SQLite DB
python scripts/run_sql_report.py         # run all 17 SQL queries, export results
python scripts/build_excel_report.py     # Excel workbook (then recalc in Excel)
python ml/train_models.py                # local ML models
python scripts/build_case_study.py       # case study Word doc
python scripts/build_market_intelligence.py
python scripts/build_ebook_charts.py
python scripts/build_ebook.py
```

## Why local ML instead of Azure Databricks

The Azure trial used for other projects in this portfolio was within days of expiring when
this build started — spinning up Databricks/Azure ML risked being cut off mid-build for no
benefit. The ML layer (`ml/train_models.py`) runs entirely on local scikit-learn instead,
with the same modeling rigor (train/test splits, honest metrics, feature importance).

---
Built by Anthony Apollis — anthony.apollis@gmail.com
