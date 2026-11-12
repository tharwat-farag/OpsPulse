
-- OpsPulse | Stockout Impact Summary by Branch

WITH latest_snapshot AS (
    SELECT MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
),

stockout_products AS (
    SELECT
        f.date_key,
        f.warehouse_key,
        f.product_key
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
        SUM(gross_profit) AS gross_profit
    FROM gold.fact_sales
    GROUP BY
        branch_key,
        product_key
),

branch_impact AS (
    SELECT
        b.branch_id,
        b.branch_name,
        so.product_key,

        COALESCE(bs.units_sold, 0) AS units_sold,
        COALESCE(bs.net_revenue, 0) AS net_revenue,
        COALESCE(bs.gross_profit, 0) AS gross_profit

    FROM stockout_products so

    JOIN gold.bridge_branch_warehouse m
        ON so.warehouse_key = m.warehouse_key
        AND m.is_primary = TRUE
        AND m.is_current = TRUE

    JOIN gold.dim_branch b
        ON m.branch_key = b.branch_key

    LEFT JOIN branch_sales bs
        ON m.branch_key = bs.branch_key
        AND so.product_key = bs.product_key
)

SELECT
    branch_id,
    branch_name,

    COUNT(DISTINCT product_key) AS stockout_products,

    COUNT(DISTINCT product_key)
        FILTER (WHERE units_sold > 0) AS stockout_products_with_sales,

    SUM(units_sold) AS annual_units_sold,
    SUM(net_revenue) AS annual_net_revenue,
    SUM(gross_profit) AS annual_gross_profit

FROM branch_impact

GROUP BY
    branch_id,
    branch_name

ORDER BY
    annual_net_revenue DESC;
