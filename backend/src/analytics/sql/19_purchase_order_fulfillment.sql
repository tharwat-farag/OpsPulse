
-- OpsPulse | Purchase Order Line Fulfillment
-- Grain: One PO Line

WITH receipt_summary AS (
    SELECT
        po_line_id,
        SUM(received_qty) AS total_received_qty,
        SUM(accepted_qty) AS total_accepted_qty,
        SUM(rejected_qty) AS total_rejected_qty,
        COUNT(*) AS receipt_events

    FROM gold.fact_goods_receipts

    GROUP BY po_line_id
),

po_line_performance AS (
    SELECT
        po.po_line_id,
        po.po_id,
        po.ordered_qty,

        COALESCE(r.total_received_qty, 0) AS total_received_qty,
        COALESCE(r.total_accepted_qty, 0) AS total_accepted_qty,
        COALESCE(r.total_rejected_qty, 0) AS total_rejected_qty,
        COALESCE(r.receipt_events, 0) AS receipt_events,

        GREATEST(
            po.ordered_qty - COALESCE(r.total_received_qty, 0),
            0
        ) AS remaining_qty,

        ROUND(
            COALESCE(r.total_received_qty, 0)::NUMERIC
            / NULLIF(po.ordered_qty, 0) * 100,
            2
        ) AS received_fulfillment_pct,

        ROUND(
            COALESCE(r.total_accepted_qty, 0)::NUMERIC
            / NULLIF(po.ordered_qty, 0) * 100,
            2
        ) AS accepted_fulfillment_pct

    FROM gold.fact_purchase_order_lines po

    LEFT JOIN receipt_summary r
        ON po.po_line_id = r.po_line_id
)

SELECT
    COUNT(*) AS total_po_lines,

    COUNT(*) FILTER (
        WHERE total_received_qty = 0
    ) AS lines_without_receipts,

    COUNT(*) FILTER (
        WHERE total_received_qty >= ordered_qty
    ) AS fully_received_lines,

    COUNT(*) FILTER (
        WHERE total_received_qty > 0
          AND total_received_qty < ordered_qty
    ) AS partially_received_lines,

    SUM(ordered_qty) AS total_ordered_qty,
    SUM(total_received_qty) AS total_received_qty,
    SUM(total_accepted_qty) AS total_accepted_qty,
    SUM(total_rejected_qty) AS total_rejected_qty,
    SUM(remaining_qty) AS remaining_qty,

    ROUND(
        SUM(total_received_qty)::NUMERIC
        / NULLIF(SUM(ordered_qty), 0) * 100,
        2
    ) AS overall_received_fulfillment_pct,

    ROUND(
        SUM(total_accepted_qty)::NUMERIC
        / NULLIF(SUM(ordered_qty), 0) * 100,
        2
    ) AS overall_accepted_fulfillment_pct,

    SUM(receipt_events) AS total_receipt_events

FROM po_line_performance;
