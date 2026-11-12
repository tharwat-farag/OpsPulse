
-- OpsPulse | Sales by Branch and Product

SELECT
    b.branch_id,
    b.branch_name,

    p.product_id,
    p.product_name,
    p.category,

    SUM(f.quantity) AS units_sold,
    SUM(f.net_revenue) AS net_revenue,
    SUM(f.gross_profit) AS gross_profit,

    COUNT(DISTINCT f.invoice_id) AS total_invoices

FROM gold.fact_sales f

JOIN gold.dim_branch b
    ON f.branch_key = b.branch_key

JOIN gold.dim_product p
    ON f.product_key = p.product_key

GROUP BY
    b.branch_id,
    b.branch_name,
    p.product_id,
    p.product_name,
    p.category

ORDER BY
    units_sold DESC

LIMIT 30;
