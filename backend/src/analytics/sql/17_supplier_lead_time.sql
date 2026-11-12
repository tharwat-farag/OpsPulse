
-- OpsPulse | Average Supplier Lead Time
-- Grain: One goods receipt event

SELECT
    s.supplier_id,
    s.supplier_name,

    COUNT(*) AS total_receipts,

    ROUND(
        AVG(gr.days_from_order)::NUMERIC,
        2
    ) AS avg_lead_time_days,

    MIN(gr.days_from_order) AS min_lead_time_days,

    MAX(gr.days_from_order) AS max_lead_time_days,

    SUM(gr.received_qty) AS total_received_qty

FROM gold.fact_goods_receipts gr

JOIN gold.dim_supplier s
    ON gr.supplier_key = s.supplier_key

GROUP BY
    s.supplier_id,
    s.supplier_name

ORDER BY
    avg_lead_time_days DESC;
