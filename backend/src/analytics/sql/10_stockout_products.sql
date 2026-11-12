
-- OpsPulse | Stockout Products by Warehouse
-- Latest available snapshot

WITH latest_snapshot AS (
    SELECT MAX(date_key) AS latest_date_key
    FROM gold.fact_inventory_snapshot
)

SELECT
    d.full_date AS snapshot_date,
    w.warehouse_name,
    p.product_id,
    p.product_name,
    p.category,

    f.quantity_on_hand,
    f.quantity_reserved,
    f.available_quantity,

    f.total_inventory_value

FROM gold.fact_inventory_snapshot f

JOIN latest_snapshot ls
    ON f.date_key = ls.latest_date_key

JOIN gold.dim_date d
    ON f.date_key = d.date_key

JOIN gold.dim_warehouse w
    ON f.warehouse_key = w.warehouse_key

JOIN gold.dim_product p
    ON f.product_key = p.product_key

WHERE f.is_stockout = TRUE

ORDER BY
    w.warehouse_name,
    p.category,
    p.product_name;
