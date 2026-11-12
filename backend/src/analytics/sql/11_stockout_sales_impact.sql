
-- OpsPulse | Stockout Products vs Annual Sales

WITH latest_snapshot AS (
    SELECT MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
),

stockout_products AS (
    SELECT
        f.warehouse_key,
        f.product_key
    FROM gold.fact_inventory_snapshot f
    JOIN latest_snapshot ls
        ON f.date_key = ls.latest_date_key
    WHERE f.is_stockout = TRUE
),

product_sales AS (
    SELECT
        product_key,
        SUM(quantity) AS units_sold,
        SUM(net_revenue) AS net_revenue,
        SUM(gross_profit) AS gross_profit,
        COUNT(DISTINCT invoice_id) AS total_invoices
    FROM gold.fact_sales
    GROUP BY product_key
)

SELECT
    w.warehouse_name,
    p.product_id,
    p.product_name,
    p.category,

    COALESCE(ps.units_sold, 0) AS annual_units_sold,
    COALESCE(ps.net_revenue, 0) AS annual_net_revenue,
    COALESCE(ps.gross_profit, 0) AS annual_gross_profit,
    COALESCE(ps.total_invoices, 0) AS total_invoices

FROM stockout_products so

JOIN gold.dim_warehouse w
    ON so.warehouse_key = w.warehouse_key

JOIN gold.dim_product p
    ON so.product_key = p.product_key

LEFT JOIN product_sales ps
    ON so.product_key = ps.product_key

ORDER BY
    annual_units_sold DESC,
    w.warehouse_name;
