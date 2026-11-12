
-- OpsPulse | Revenue by Branch

SELECT
    b.branch_id,
    b.branch_name,
    b.region,

    COUNT(DISTINCT f.invoice_id) AS total_invoices,

    SUM(f.quantity) AS units_sold,

    SUM(f.net_revenue) AS net_revenue,

    SUM(f.gross_profit) AS gross_profit,

    ROUND(
        SUM(f.gross_profit)
        / NULLIF(SUM(f.net_revenue), 0) * 100,
        2
    ) AS gross_profit_margin_pct

FROM gold.fact_sales f

JOIN gold.dim_branch b
    ON f.branch_key = b.branch_key

GROUP BY
    b.branch_id,
    b.branch_name,
    b.region

ORDER BY net_revenue DESC;
