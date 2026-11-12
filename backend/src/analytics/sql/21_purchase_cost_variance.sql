
-- OpsPulse | Purchase Cost Variance
-- Grain: One Purchase Order Line

WITH purchase_cost_comparison AS (
    SELECT
        po.po_line_id,
        po.po_id,
        po.product_key,
        po.supplier_key,
        po.ordered_qty,

        po.unit_cost AS actual_unit_cost,
        bps.supplier_price AS reference_supplier_price,

        po.line_total AS actual_line_cost,

        (
            po.unit_cost - bps.supplier_price
        ) AS unit_cost_variance,

        (
            po.unit_cost - bps.supplier_price
        ) * po.ordered_qty AS total_cost_variance

    FROM gold.fact_purchase_order_lines po

    INNER JOIN gold.bridge_product_supplier bps
        ON po.product_key = bps.product_key
       AND po.supplier_key = bps.supplier_key
),

variance_metrics AS (
    SELECT
        *,

        ROUND(
            unit_cost_variance::NUMERIC
            / NULLIF(reference_supplier_price, 0) * 100,
            2
        ) AS cost_variance_pct

    FROM purchase_cost_comparison
)

SELECT
    COUNT(*) AS total_po_lines,

    COUNT(*) FILTER (
        WHERE unit_cost_variance > 0
    ) AS above_reference_price_lines,

    COUNT(*) FILTER (
        WHERE unit_cost_variance < 0
    ) AS below_reference_price_lines,

    COUNT(*) FILTER (
        WHERE unit_cost_variance = 0
    ) AS matching_reference_price_lines,

    ROUND(
        SUM(actual_line_cost),
        2
    ) AS total_actual_purchase_cost,

    ROUND(
        SUM(reference_supplier_price * ordered_qty),
        2
    ) AS total_reference_purchase_cost,

    ROUND(
        SUM(total_cost_variance),
        2
    ) AS total_purchase_cost_variance,

    ROUND(
        SUM(total_cost_variance)
        / NULLIF(
            SUM(reference_supplier_price * ordered_qty),
            0
        ) * 100,
        2
    ) AS overall_cost_variance_pct,

    ROUND(
        AVG(cost_variance_pct),
        2
    ) AS avg_line_cost_variance_pct

FROM variance_metrics;
