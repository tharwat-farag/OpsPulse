
-- OpsPulse | Operating Expenses by Branch

SELECT
    b.branch_id,
    b.branch_name,

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

JOIN gold.dim_branch b
    ON f.branch_key = b.branch_key

GROUP BY
    b.branch_id,
    b.branch_name

ORDER BY
    total_expenses DESC;
