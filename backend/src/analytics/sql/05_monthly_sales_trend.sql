
-- OpsPulse | Monthly Sales Trend

WITH monthly_sales AS (
    SELECT
        d.year_number,
        d.month_number,
        d.month_name,
        d.year_month,

        SUM(f.gross_amount) AS gross_revenue,
        SUM(f.discount_amount) AS total_discounts,
        SUM(f.net_revenue) AS net_revenue,
        SUM(f.total_cost) AS total_cost,
        SUM(f.gross_profit) AS gross_profit,

        COUNT(DISTINCT f.invoice_id) AS total_invoices

    FROM gold.fact_sales f

    JOIN gold.dim_date d
        ON f.date_key = d.date_key

    GROUP BY
        d.year_number,
        d.month_number,
        d.month_name,
        d.year_month
),

sales_with_previous_month AS (
    SELECT
        *,

        LAG(net_revenue) OVER (
            ORDER BY year_number, month_number
        ) AS previous_month_revenue

    FROM monthly_sales
)

SELECT
    year_number,
    month_number,
    month_name,
    year_month,

    total_invoices,
    gross_revenue,
    total_discounts,
    net_revenue,
    total_cost,
    gross_profit,

    ROUND(
        gross_profit / NULLIF(net_revenue, 0) * 100,
        2
    ) AS gross_profit_margin_pct,

    previous_month_revenue,

    ROUND(
        (net_revenue - previous_month_revenue)
        / NULLIF(previous_month_revenue, 0) * 100,
        2
    ) AS revenue_growth_pct

FROM sales_with_previous_month

ORDER BY year_number, month_number;
