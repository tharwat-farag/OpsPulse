
-- OpsPulse | Stockout Analysis by Warehouse
-- Latest available snapshot only

WITH latest_snapshot AS (
    SELECT MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
)

SELECT
    w.warehouse_id,
    w.warehouse_name,

    COUNT(*) AS inventory_records,

    COUNT(*) FILTER (
        WHERE f.is_stockout = TRUE
    ) AS stockout_records,

    ROUND(
        COUNT(*) FILTER (WHERE f.is_stockout = TRUE)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS stockout_rate_pct,

    SUM(f.quantity_on_hand) AS total_quantity_on_hand,
    SUM(f.available_quantity) AS total_available_quantity,

    SUM(f.total_inventory_value) AS inventory_value

FROM gold.fact_inventory_snapshot f

JOIN latest_snapshot ls
    ON f.date_key = ls.latest_date_key

JOIN gold.dim_warehouse w
    ON f.warehouse_key = w.warehouse_key

GROUP BY
    w.warehouse_id,
    w.warehouse_name

ORDER BY
    stockout_rate_pct DESC;
