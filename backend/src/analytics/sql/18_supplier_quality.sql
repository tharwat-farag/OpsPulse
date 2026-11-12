
-- OpsPulse | Supplier Goods Receipt Quality
-- Grain: Supplier

SELECT
    s.supplier_id,
    s.supplier_name,

    COUNT(*) AS total_receipts,

    SUM(gr.received_qty) AS total_received_qty,

    SUM(gr.accepted_qty) AS total_accepted_qty,

    SUM(gr.rejected_qty) AS total_rejected_qty,

    ROUND(
        SUM(gr.accepted_qty)::NUMERIC
        / NULLIF(SUM(gr.received_qty), 0) * 100,
        2
    ) AS acceptance_rate_pct,

    ROUND(
        SUM(gr.rejected_qty)::NUMERIC
        / NULLIF(SUM(gr.received_qty), 0) * 100,
        2
    ) AS rejection_rate_pct

FROM gold.fact_goods_receipts gr

JOIN gold.dim_supplier s
    ON gr.supplier_key = s.supplier_key

GROUP BY
    s.supplier_id,
    s.supplier_name

ORDER BY
    acceptance_rate_pct ASC;
