
-- OpsPulse | Latest Inventory Position

WITH latest_snapshot AS (
    SELECT
        MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
)

SELECT
    d.full_date AS snapshot_date,

    COUNT(*) AS inventory_records,

    COUNT(DISTINCT f.product_key) AS total_products,
    COUNT(DISTINCT f.warehouse_key) AS total_warehouses,

    SUM(f.quantity_on_hand) AS total_quantity_on_hand,
    SUM(f.quantity_reserved) AS total_quantity_reserved,
    SUM(f.available_quantity) AS total_available_quantity,

    SUM(f.total_inventory_value) AS total_inventory_value,
    SUM(f.available_inventory_value) AS available_inventory_value,

    COUNT(*) FILTER (
        WHERE f.is_stockout = TRUE
    ) AS stockout_records,

    ROUND(
        COUNT(*) FILTER (WHERE f.is_stockout = TRUE)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS stockout_rate_pct

FROM gold.fact_inventory_snapshot f

JOIN latest_snapshot ls
    ON f.date_key = ls.latest_date_key

JOIN gold.dim_date d
    ON f.date_key = d.date_key

GROUP BY
    d.full_date;
