-- CityHire Fleet & Stock Intelligence
-- SQL analysis layer mapped directly to the Data & Automation Analyst project brief.
-- Target DB: data/processed/cityhire_fleet.db (SQLite; syntax is portable to
-- T-SQL/OData-backed SQL views with minor date-function changes).

-- =============================================================================
-- 1) WORKSHOP IN-SERVICE % — 6-12 month success point: workshop % down to 15%
-- =============================================================================
-- Daily in-service % by depot (in-service = 100% - workshop%), trended monthly.
SELECT
    strftime('%Y-%m', date)              AS month,
    depot,
    ROUND(AVG(100.0 - workshop_pct), 2)  AS avg_in_service_pct,
    ROUND(AVG(workshop_pct), 2)          AS avg_workshop_pct,
    CASE WHEN AVG(workshop_pct) <= 15 THEN 'ON TARGET' ELSE 'ABOVE TARGET' END AS target_15pct_status
FROM daily_stock_stats
GROUP BY month, depot
ORDER BY month, depot;

-- Fleet-wide workshop % trend (single KPI line for exec dashboard)
SELECT
    strftime('%Y-%m', date)     AS month,
    ROUND(AVG(workshop_pct), 2) AS fleet_workshop_pct
FROM daily_stock_stats
GROUP BY month
ORDER BY month;

-- =============================================================================
-- 2) UTILISATION — success point: maintained above 60%
-- =============================================================================
SELECT
    category,
    ROUND(AVG(utilisation_pct), 2) AS avg_utilisation_pct,
    CASE WHEN AVG(utilisation_pct) >= 60 THEN 'ON TARGET' ELSE 'BELOW TARGET' END AS target_60pct_status
FROM daily_stock_stats
WHERE date >= date((SELECT MAX(date) FROM daily_stock_stats), '-90 days')
GROUP BY category
ORDER BY avg_utilisation_pct ASC;

-- Depots trending below the 60% utilisation floor in the last 30 days (action list)
SELECT
    depot,
    ROUND(AVG(utilisation_pct), 2) AS avg_utilisation_pct_30d
FROM daily_stock_stats
WHERE date >= date((SELECT MAX(date) FROM daily_stock_stats), '-30 days')
GROUP BY depot
HAVING AVG(utilisation_pct) < 60
ORDER BY avg_utilisation_pct_30d ASC;

-- =============================================================================
-- 3) CAPEX vs BUDGET — success point: capex spend not exceeding budget
-- =============================================================================
SELECT
    category,
    ROUND(SUM(budget_gbp), 2)        AS ytd_budget_gbp,
    ROUND(SUM(actual_spend_gbp), 2)  AS ytd_actual_gbp,
    ROUND(SUM(actual_spend_gbp) - SUM(budget_gbp), 2) AS ytd_variance_gbp,
    ROUND(100.0 * SUM(actual_spend_gbp) / NULLIF(SUM(budget_gbp), 0), 1) AS pct_of_budget_used
FROM capex_monthly
GROUP BY category
ORDER BY ytd_variance_gbp DESC;

-- Months where fleet-wide spend exceeded budget (exception report for senior mgmt)
SELECT
    month,
    ROUND(SUM(budget_gbp), 2)       AS total_budget_gbp,
    ROUND(SUM(actual_spend_gbp), 2) AS total_actual_gbp,
    ROUND(SUM(actual_spend_gbp) - SUM(budget_gbp), 2) AS variance_gbp
FROM capex_monthly
GROUP BY month
HAVING SUM(actual_spend_gbp) > SUM(budget_gbp)
ORDER BY month;

-- =============================================================================
-- 4) DAILY STOCK STATS (JD: "daily stock stats" done daily)
-- =============================================================================
SELECT
    depot,
    category,
    fleet_units,
    units_on_hire,
    units_in_workshop,
    units_available,
    utilisation_pct,
    workshop_pct
FROM daily_stock_stats
WHERE date = (SELECT MAX(date) FROM daily_stock_stats)
ORDER BY depot, category;

-- =============================================================================
-- 5) FLEETING / STOCK SHORTAGE BALANCING between depots (JD daily task)
-- =============================================================================
SELECT
    category,
    from_depot,
    to_depot,
    COUNT(*)                                   AS transfer_count,
    SUM(units_transferred)                     AS total_units_moved,
    ROUND(100.0 * SUM(fulfilled) / COUNT(*), 1) AS pct_fulfilled
FROM stock_transfers
GROUP BY category, from_depot, to_depot
ORDER BY transfer_count DESC
LIMIT 25;

-- Unfulfilled shortage requests requiring action
SELECT transfer_id, date, category, from_depot, to_depot, units_transferred, reason
FROM stock_transfers
WHERE fulfilled = 0
ORDER BY date DESC;

-- =============================================================================
-- 6) MINIMUM STOCK LEVELS (JD: management/maintenance of minimum stock levels)
-- =============================================================================
-- Current available units at each depot vs each asset's minimum stock level.
SELECT
    sm.category,
    sm.depot,
    COUNT(*)                                        AS assets_of_type,
    SUM(CASE WHEN sm.status = 'Available' THEN 1 ELSE 0 END) AS units_available,
    MAX(sm.min_stock_level)                          AS min_stock_level,
    CASE WHEN SUM(CASE WHEN sm.status = 'Available' THEN 1 ELSE 0 END) < MAX(sm.min_stock_level)
         THEN 'BELOW MINIMUM' ELSE 'OK' END          AS stock_level_flag
FROM stock_master sm
GROUP BY sm.category, sm.depot
HAVING stock_level_flag = 'BELOW MINIMUM'
ORDER BY sm.category, sm.depot;

-- =============================================================================
-- 7) AUCTION & PARTS APPROVALS >£500 (JD daily task)
-- =============================================================================
SELECT
    approval_id, stock_code, category, request_type, value_gbp, requested_date, status, requested_by
FROM approvals
WHERE status = 'Pending'
ORDER BY value_gbp DESC;

SELECT
    request_type,
    COUNT(*)                         AS requests,
    ROUND(SUM(value_gbp), 2)         AS total_value_gbp,
    ROUND(AVG(value_gbp), 2)         AS avg_value_gbp,
    SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved,
    SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) AS rejected
FROM approvals
GROUP BY request_type;

-- =============================================================================
-- 8) EXTERNAL REPAIRS + APPROVAL OVERSIGHT (JD daily task)
-- =============================================================================
SELECT
    supplier,
    COUNT(*)                            AS repair_jobs,
    ROUND(SUM(cost_gbp), 2)             AS total_cost_gbp,
    ROUND(AVG(days_out_of_service), 1)  AS avg_days_out_of_service,
    SUM(CASE WHEN requires_approval AND approval_status = 'Pending' THEN 1 ELSE 0 END) AS pending_approvals
FROM external_repairs
GROUP BY supplier
ORDER BY total_cost_gbp DESC;

-- Repairs pending approval right now (>£500, needs Ops & Systems Manager sign-off)
SELECT repair_id, stock_code, category, supplier, fault_reported, cost_gbp, date_logged
FROM external_repairs
WHERE requires_approval = 1 AND approval_status = 'Pending'
ORDER BY cost_gbp DESC;

-- =============================================================================
-- 9) ROI REPORT (JD: production of stock and ROI reports to aid decision making)
-- =============================================================================
-- Estimated annualised hire revenue = day_rate * utilisation% * 365, vs capex outlay.
SELECT
    category,
    COUNT(*)                                                        AS units,
    ROUND(SUM(capex_gbp), 2)                                        AS total_capex_gbp,
    ROUND(AVG(utilisation_pct_ytd), 1)                              AS avg_utilisation_pct,
    ROUND(SUM(day_rate_gbp * utilisation_pct_ytd / 100.0 * 365), 2) AS est_annual_revenue_gbp,
    ROUND(100.0 * SUM(day_rate_gbp * utilisation_pct_ytd / 100.0 * 365)
          / NULLIF(SUM(capex_gbp), 0), 1)                           AS est_roi_pct
FROM stock_master
GROUP BY category
ORDER BY est_roi_pct DESC;

-- Lowest-ROI individual assets — candidates for auction/disposal review
SELECT
    stock_code, category, product_name, depot, capex_gbp, book_value_gbp,
    utilisation_pct_ytd, condition, status,
    ROUND(day_rate_gbp * utilisation_pct_ytd / 100.0 * 365, 2) AS est_annual_revenue_gbp,
    ROUND(100.0 * (day_rate_gbp * utilisation_pct_ytd / 100.0 * 365) / NULLIF(capex_gbp, 0), 1) AS est_roi_pct
FROM stock_master
WHERE status != 'Auction Pending'
ORDER BY est_roi_pct ASC
LIMIT 30;

-- =============================================================================
-- 10) NEW PRODUCT LINE / MARKET GAP SIGNAL (JD: recommendations for new product lines)
-- =============================================================================
-- Categories with sustained utilisation > 85% AND workshop% low = under-supplied,
-- strong candidate for capex expansion or new adjacent product line.
SELECT
    category,
    ROUND(AVG(utilisation_pct), 1) AS avg_utilisation_pct_90d,
    ROUND(AVG(workshop_pct), 1)    AS avg_workshop_pct_90d
FROM daily_stock_stats
WHERE date >= date((SELECT MAX(date) FROM daily_stock_stats), '-90 days')
GROUP BY category
HAVING avg_utilisation_pct_90d > 85
ORDER BY avg_utilisation_pct_90d DESC;
