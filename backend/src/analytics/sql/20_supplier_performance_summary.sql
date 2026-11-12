
-- OpsPulse | Supplier Performance Summary

WITH delivery_metrics AS (
    SELECT
        supplier_key,
        COUNT(*) AS total_receipts,

        COUNT(*) FILTER (
            WHERE is_late_receipt = FALSE
        ) AS on_time_receipts,

        ROUND(
            COUNT(*) FILTER (
                WHERE is_late_receipt = FALSE
            )::NUMERIC
            / NULLIF(COUNT(*), 0) * 100,
            2
        ) AS on_time_delivery_rate_pct,

        ROUND(
            AVG(days_from_order)::NUMERIC,
            2
        ) AS avg_lead_time_days

    FROM gold.fact_goods_receipts
    GROUP BY supplier_key
),

quality_metrics AS (
    SELECT
        supplier_key,
        SUM(received_qty) AS total_received_qty,
        SUM(accepted_qty) AS total_accepted_qty,
        SUM(rejected_qty) AS total_rejected_qty,

        ROUND(
            SUM(accepted_qty)::NUMERIC
            / NULLIF(SUM(received_qty), 0) * 100,
            2
        ) AS acceptance_rate_pct

    FROM gold.fact_goods_receipts
    GROUP BY supplier_key
)

SELECT
    s.supplier_id,
    s.supplier_name,

    d.total_receipts,
    d.on_time_receipts,
    d.on_time_delivery_rate_pct,
    d.avg_lead_time_days,

    q.total_received_qty,
    q.total_accepted_qty,
    q.total_rejected_qty,
    q.acceptance_rate_pct

FROM gold.dim_supplier s

LEFT JOIN delivery_metrics d
    ON s.supplier_key = d.supplier_key

LEFT JOIN quality_metrics q
    ON s.supplier_key = q.supplier_key

ORDER BY
    d.on_time_delivery_rate_pct ASC;
