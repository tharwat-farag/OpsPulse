
-- ==========================================
-- OpsPulse | Sales Intelligence
-- KPI 01: Sales Overview
-- ==========================================

SELECT
    COUNT(*) AS total_sales_lines,

    COUNT(DISTINCT invoice_id) AS total_invoices,

    SUM(quantity) AS total_units_sold,

    SUM(gross_amount) AS gross_revenue,

    SUM(discount_amount) AS total_discounts,

    SUM(net_revenue) AS net_revenue,

    SUM(total_cost) AS total_cost,

    SUM(gross_profit) AS gross_profit,

    ROUND(
        SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100,
        2
    ) AS gross_profit_margin_pct

FROM gold.fact_sales;
