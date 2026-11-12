
-- OpsPulse | Stockout Impact by Branch
-- Latest inventory snapshot mapped to served branches

WITH latest_snapshot AS (
    SELECT MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
),

stockout_products AS (
    SELECT
        f.date_key,
        f.warehouse_key,
        f.product_key,
        f.quantity_on_hand,
        f.quantity_reserved,
        f.available_quantity,
        f.total_inventory_value
    FROM gold.fact_inventory_snapshot f

    JOIN latest_snapshot ls
        ON f.date_key = ls.latest_date_key

    WHERE f.is_stockout = TRUE
),

branch_sales AS (
    SELECT
        branch_key,
        product_key,

        SUM(quantity) AS units_sold,
        SUM(net_revenue) AS net_revenue,
        SUM(gross_profit) AS gross_profit,
        COUNT(DISTINCT invoice_id) AS total_invoices

    FROM gold.fact_sales

    GROUP BY
        branch_key,
        product_key
)

SELECT
    d.full_date AS snapshot_date,

    b.branch_id,
    b.branch_name,

    w.warehouse_id,
    w.warehouse_name,

    p.product_id,
    p.product_name,
    p.category,

    so.quantity_on_hand,
    so.quantity_reserved,
    so.available_quantity,

    COALESCE(bs.units_sold, 0) AS branch_annual_units_sold,
    COALESCE(bs.net_revenue, 0) AS branch_annual_net_revenue,
    COALESCE(bs.gross_profit, 0) AS branch_annual_gross_profit,
    COALESCE(bs.total_invoices, 0) AS branch_total_invoices

FROM stockout_products so

JOIN gold.dim_date d
    ON so.date_key = d.date_key

JOIN gold.bridge_branch_warehouse m
    ON so.warehouse_key = m.warehouse_key
    AND d.full_date >= m.valid_from
    AND d.full_date < m.valid_to
    AND m.is_primary = TRUE

JOIN gold.dim_branch b
    ON m.branch_key = b.branch_key

JOIN gold.dim_warehouse w
    ON so.warehouse_key = w.warehouse_key

JOIN gold.dim_product p
    ON so.product_key = p.product_key

LEFT JOIN branch_sales bs
    ON m.branch_key = bs.branch_key
    AND so.product_key = bs.product_key

ORDER BY
    branch_annual_units_sold DESC,
    b.branch_id,
    p.product_id;
