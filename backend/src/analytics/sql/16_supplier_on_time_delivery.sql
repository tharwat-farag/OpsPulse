
-- OpsPulse | Supplier On-Time Delivery Performance
-- Grain: One goods receipt event

SELECT
    s.supplier_id,
    s.supplier_name,

    COUNT(*) AS total_receipts,

    COUNT(*) FILTER (
        WHERE gr.is_late_receipt = FALSE
    ) AS on_time_receipts,

    COUNT(*) FILTER (
        WHERE gr.is_late_receipt = TRUE
    ) AS late_receipts,

    ROUND(
        COUNT(*) FILTER (
            WHERE gr.is_late_receipt = FALSE
        )::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS on_time_delivery_rate_pct,

    ROUND(
        AVG(gr.days_after_expected)::NUMERIC,
        2
    ) AS avg_days_after_expected,

    SUM(gr.received_qty) AS total_received_qty

FROM gold.fact_goods_receipts gr

JOIN gold.dim_supplier s
    ON gr.supplier_key = s.supplier_key

GROUP BY
    s.supplier_id,
    s.supplier_name

ORDER BY
    on_time_delivery_rate_pct ASC,
    total_receipts DESC;
