
-- OpsPulse | Revenue by Sales Channel

SELECT
    c.sales_channel_name,

    COUNT(*) AS total_sales_lines,
    COUNT(DISTINCT f.invoice_id) AS total_invoices,

    SUM(f.quantity) AS units_sold,
    SUM(f.net_revenue) AS net_revenue,
    SUM(f.total_cost) AS total_cost,
    SUM(f.gross_profit) AS gross_profit,

    ROUND(
        SUM(f.gross_profit)
        / NULLIF(SUM(f.net_revenue), 0) * 100,
        2
    ) AS gross_profit_margin_pct,

    ROUND(
        SUM(f.net_revenue)
        / NULLIF(
            SUM(SUM(f.net_revenue)) OVER (),
            0
        ) * 100,
        2
    ) AS revenue_contribution_pct

FROM gold.fact_sales f

JOIN gold.dim_sales_channel c
    ON f.sales_channel_key = c.sales_channel_key

GROUP BY
    c.sales_channel_name

ORDER BY
    net_revenue DESC;
