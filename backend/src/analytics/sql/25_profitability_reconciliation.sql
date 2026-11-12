
-- OpsPulse | Profitability Reconciliation

WITH sales_totals AS (
    SELECT
        SUM(net_revenue) AS net_revenue,
        SUM(gross_profit) AS gross_profit
    FROM gold.fact_sales
),

expense_totals AS (
    SELECT
        SUM(amount) AS operating_expenses
    FROM gold.fact_operating_expenses
),

branch_results AS (
    SELECT
        b.branch_key,
        COALESCE(s.gross_profit, 0)
        - COALESCE(e.operating_expenses, 0)
            AS operating_result

    FROM gold.dim_branch b

    LEFT JOIN (
        SELECT
            branch_key,
            SUM(gross_profit) AS gross_profit
        FROM gold.fact_sales
        GROUP BY branch_key
    ) s
        ON b.branch_key = s.branch_key

    LEFT JOIN (
        SELECT
            branch_key,
            SUM(amount) AS operating_expenses
        FROM gold.fact_operating_expenses
        GROUP BY branch_key
    ) e
        ON b.branch_key = e.branch_key
)

SELECT
    ROUND(st.net_revenue, 2) AS total_net_revenue,

    ROUND(st.gross_profit, 2) AS total_gross_profit,

    ROUND(et.operating_expenses, 2) AS total_operating_expenses,

    ROUND(
        st.gross_profit - et.operating_expenses,
        2
    ) AS overall_simplified_operating_result,

    ROUND(
        SUM(br.operating_result),
        2
    ) AS sum_of_branch_results,

    ROUND(
        st.gross_profit - et.operating_expenses
        - SUM(br.operating_result),
        2
    ) AS reconciliation_difference

FROM sales_totals st
CROSS JOIN expense_totals et
CROSS JOIN branch_results br

GROUP BY
    st.net_revenue,
    st.gross_profit,
    et.operating_expenses;
