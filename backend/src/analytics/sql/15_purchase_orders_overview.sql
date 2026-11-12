
-- OpsPulse | Purchase Orders Overview

WITH purchase_orders AS (
    -- Convert PO lines into one record per purchase order
    SELECT
        po_id,
        order_status,
        SUM(ordered_qty) AS total_ordered_qty,
        SUM(line_total) AS total_order_value

    FROM gold.fact_purchase_order_lines

    GROUP BY
        po_id,
        order_status
)

SELECT
    COUNT(*) AS total_purchase_orders,

    COUNT(*) FILTER (
        WHERE order_status = 'Fully Received'
    ) AS fully_received_orders,

    COUNT(*) FILTER (
        WHERE order_status = 'Partially Received'
    ) AS partially_received_orders,

    COUNT(*) FILTER (
        WHERE order_status = 'Pending'
    ) AS pending_orders,

    COUNT(*) FILTER (
        WHERE order_status = 'Cancelled'
    ) AS cancelled_orders,

    SUM(total_ordered_qty) AS total_ordered_quantity,

    SUM(total_order_value) AS total_purchase_order_value,

    ROUND(
        COUNT(*) FILTER (
            WHERE order_status = 'Fully Received'
        )::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS fully_received_rate_pct,

    ROUND(
        COUNT(*) FILTER (
            WHERE order_status = 'Partially Received'
        )::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS partially_received_rate_pct,

    ROUND(
        COUNT(*) FILTER (
            WHERE order_status = 'Pending'
        )::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS pending_rate_pct,

    ROUND(
        COUNT(*) FILTER (
            WHERE order_status = 'Cancelled'
        )::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS cancelled_rate_pct

FROM purchase_orders;
