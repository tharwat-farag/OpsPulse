
-- OpsPulse | Operating Expenses Overview

SELECT
    ec.expense_category_name,

    COUNT(*) AS expense_transactions,

    ROUND(
        SUM(f.amount),
        2
    ) AS total_expenses,

    ROUND(
        AVG(f.amount),
        2
    ) AS average_expense,

    ROUND(
        SUM(f.amount)
        / NULLIF(
            SUM(SUM(f.amount)) OVER (),
            0
        ) * 100,
        2
    ) AS expense_contribution_pct

FROM gold.fact_operating_expenses f

JOIN gold.dim_expense_category ec
    ON f.expense_category_key = ec.expense_category_key

GROUP BY
    ec.expense_category_name

ORDER BY
    total_expenses DESC;
