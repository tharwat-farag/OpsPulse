
-- OpsPulse | Simplified Operating Result by Branch

WITH branch_sales AS (
    SELECT
        branch_key,
        SUM(net_revenue) AS net_revenue,
        SUM(total_cost) AS total_cost,
        SUM(gross_profit) AS gross_profit,
        COUNT(DISTINCT invoice_id) AS total_invoices

    FROM gold.fact_sales

    GROUP BY branch_key
),

branch_expenses AS (
    SELECT
        branch_key,
        SUM(amount) AS operating_expenses,
        COUNT(*) AS expense_transactions

    FROM gold.fact_operating_expenses

    GROUP BY branch_key
)

SELECT
    b.branch_id,
    b.branch_name,

    ROUND(COALESCE(s.net_revenue, 0), 2) AS net_revenue,

    ROUND(COALESCE(s.total_cost, 0), 2) AS total_cost,

    ROUND(COALESCE(s.gross_profit, 0), 2) AS gross_profit,

    ROUND(COALESCE(e.operating_expenses, 0), 2)
        AS operating_expenses,

    ROUND(
        COALESCE(s.gross_profit, 0)
        - COALESCE(e.operating_expenses, 0),
        2
    ) AS simplified_operating_result,

    ROUND(
        (
            COALESCE(s.gross_profit, 0)
            - COALESCE(e.operating_expenses, 0)
        ) / NULLIF(s.net_revenue, 0) * 100,
        2
    ) AS simplified_operating_margin_pct,

    COALESCE(s.total_invoices, 0) AS total_invoices,

    COALESCE(e.expense_transactions, 0)
        AS expense_transactions

FROM gold.dim_branch b

LEFT JOIN branch_sales s
    ON b.branch_key = s.branch_key

LEFT JOIN branch_expenses e
    ON b.branch_key = e.branch_key

ORDER BY
    simplified_operating_result DESC;
