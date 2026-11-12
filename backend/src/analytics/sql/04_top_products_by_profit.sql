
-- OpsPulse | Top Products by Gross Profit

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.brand,

    SUM(f.quantity) AS units_sold,

    SUM(f.net_revenue) AS net_revenue,

    SUM(f.gross_profit) AS gross_profit,

    ROUND(
        SUM(f.gross_profit)
        / NULLIF(SUM(f.net_revenue), 0) * 100,
        2
    ) AS gross_profit_margin_pct

FROM gold.fact_sales f

JOIN gold.dim_product p
    ON f.product_key = p.product_key

GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.brand

ORDER BY gross_profit DESC

LIMIT 10;
