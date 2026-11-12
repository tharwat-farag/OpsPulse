
-- OpsPulse | Inventory Health Overview

SELECT
    COUNT(*) AS total_inventory_records,

    COUNT(DISTINCT product_key) AS total_products,
    COUNT(DISTINCT warehouse_key) AS total_warehouses,

    SUM(quantity_on_hand) AS total_quantity_on_hand,
    SUM(quantity_reserved) AS total_quantity_reserved,
    SUM(available_quantity) AS total_available_quantity,

    SUM(total_inventory_value) AS total_inventory_value,
    SUM(available_inventory_value) AS available_inventory_value,
    SUM(reserved_inventory_value) AS reserved_inventory_value,

    COUNT(*) FILTER (
        WHERE is_stockout = TRUE
    ) AS stockout_records,

    ROUND(
        COUNT(*) FILTER (WHERE is_stockout = TRUE)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS stockout_rate_pct,

    ROUND(
        SUM(quantity_reserved)::NUMERIC
        / NULLIF(SUM(quantity_on_hand), 0) * 100,
        2
    ) AS reserved_quantity_pct,

    ROUND(
        AVG(capacity_utilization_pct),
        2
    ) AS avg_capacity_utilization_pct

FROM gold.fact_inventory_snapshot;
