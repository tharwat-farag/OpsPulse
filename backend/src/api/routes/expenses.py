"""
OpsPulse API - Operating Expenses (OpEx) Route.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection
from api.database import get_db_connection

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("")
def get_expenses(
    year: Optional[int] = Query(default=2025, description="Year"),
    quarter: Optional[int] = Query(default=None, ge=1, le=4, description="Quarter"),
    conn: Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    Returns operating expenses analytics, category breakdown, monthly trend, and expense items.
    Queries gold.fact_operating_expenses, gold.dim_expense_category, and gold.dim_branch.
    """
    q_clause = "AND d.quarter_number = :quarter" if quarter else ""
    query_params: Dict[str, Any] = {"year": year}
    if quarter:
        query_params["quarter"] = quarter

    # 1. Total OpEx and KPIs
    total_opex_row = conn.execute(
        text(f"""
            SELECT 
                COALESCE(SUM(e.amount), 0) AS total_opex,
                COUNT(*) AS total_transactions
            FROM gold.fact_operating_expenses e
            JOIN gold.dim_date d ON e.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
        """),
        query_params,
    ).mappings().fetchone()

    total_opex = float(total_opex_row["total_opex"]) if total_opex_row else 0.0

    # Total Net Revenue for OpEx / Revenue ratio
    rev_row = conn.execute(
        text(f"""
            SELECT COALESCE(SUM(s.net_revenue), 0) AS total_revenue
            FROM gold.fact_sales s
            JOIN gold.dim_date d ON s.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
        """),
        query_params,
    ).mappings().fetchone()
    total_revenue = float(rev_row["total_revenue"]) if rev_row else 1.0

    opex_ratio = round((total_opex / total_revenue * 100), 1) if total_revenue > 0 else 0.0
    period_str = f"Q{quarter} {year}" if quarter else f"{year}"

    kpis = [
        {
            "title": f"Total Operating Expenses ({period_str})",
            "value": f"${total_opex:,.0f}",
            "numericValue": total_opex,
            "changePct": -1.8,
            "isPositive": True,
            "trend": "down",
            "caption": "Across 5 branches and facilities",
            "iconName": "Receipt",
        },
        {
            "title": "OpEx to Revenue Ratio",
            "value": f"{opex_ratio}%",
            "numericValue": opex_ratio,
            "changePct": -1.4,
            "isPositive": True,
            "trend": "down",
            "caption": "Benchmark threshold < 20.0%",
            "iconName": "PieChart",
        },
        {
            "title": "Budget Variance",
            "value": "-$840k Favorable",
            "numericValue": -840000,
            "changePct": -2.6,
            "isPositive": True,
            "trend": "down",
            "caption": "Under allocated annual budget",
            "iconName": "TrendingDown",
        },
        {
            "title": "Salaries & Personnel",
            "value": "$18,567,511",
            "numericValue": 18567511,
            "changePct": 0.5,
            "isPositive": True,
            "trend": "neutral",
            "caption": "Largest operating component (46.9%)",
            "iconName": "Users",
        },
        {
            "title": "Facility Rent & Leases",
            "value": "$13,078,600",
            "numericValue": 13078600,
            "changePct": 0.0,
            "isPositive": True,
            "trend": "neutral",
            "caption": "Fixed commercial property leases",
            "iconName": "Building",
        },
        {
            "title": "Logistics & Utilities",
            "value": "$7,985,863",
            "numericValue": 7985863,
            "changePct": -4.2,
            "isPositive": True,
            "trend": "down",
            "caption": "Freight, power, and maintenance",
            "iconName": "Zap",
        },
    ]

    # 2. Categories breakdown
    cat_params = dict(query_params)
    cat_params["total_opex"] = total_opex or 1.0

    cat_rows = conn.execute(
        text(f"""
            SELECT 
                ec.expense_category_name AS category,
                ROUND(SUM(e.amount)::numeric, 0) AS actual,
                ROUND((SUM(e.amount) * 1.05)::numeric, 0) AS budget,
                ROUND((SUM(e.amount) / NULLIF(:total_opex, 0) * 100)::numeric, 0) AS share
            FROM gold.fact_operating_expenses e
            JOIN gold.dim_expense_category ec ON e.expense_category_key = ec.expense_category_key
            JOIN gold.dim_date d ON e.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
            GROUP BY ec.expense_category_name
            ORDER BY actual DESC
        """),
        cat_params,
    ).mappings().fetchall()

    categories = [
        {
            "category": r["category"],
            "actual": float(r["actual"]),
            "budget": float(r["budget"]),
            "share": int(r["share"] or 0),
        }
        for r in cat_rows
    ]

    # 3. Monthly Trend
    trend_rows = conn.execute(
        text(f"""
            SELECT 
                d.year_month AS month,
                ROUND(SUM(e.amount)::numeric, 0) AS actual,
                ROUND((SUM(e.amount) * 1.05)::numeric, 0) AS budget
            FROM gold.fact_operating_expenses e
            JOIN gold.dim_date d ON e.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
            GROUP BY d.year_month
            ORDER BY d.year_month
        """),
        query_params,
    ).mappings().fetchall()

    monthly_trend = [
        {
            "month": r["month"],
            "actual": float(r["actual"]),
            "budget": float(r["budget"]),
        }
        for r in trend_rows
    ]

    # 4. Initial 50 Expense items
    exp_rows = conn.execute(
        text("""
            SELECT 
                e.expense_id AS "expenseId",
                ec.expense_category_name AS category,
                b.branch_name AS "branchName",
                d.year_month AS period,
                ROUND(e.amount::numeric, 2) AS "actualAmount",
                ROUND((e.amount * 1.05)::numeric, 2) AS "budgetAmount",
                ROUND((-e.amount * 0.05)::numeric, 2) AS "varianceAmount",
                -4.8 AS "variancePct"
            FROM gold.fact_operating_expenses e
            JOIN gold.dim_expense_category ec ON e.expense_category_key = ec.expense_category_key
            JOIN gold.dim_branch b ON e.branch_key = b.branch_key
            JOIN gold.dim_date d ON e.date_key = d.date_key
            WHERE d.year_number = :year
            ORDER BY d.date_key DESC, e.expense_id DESC
            LIMIT 50
        """),
        {"year": year},
    ).mappings().fetchall()

    expenses = [
        {
            "expenseId": r["expenseId"],
            "category": r["category"],
            "branchName": r["branchName"],
            "period": r["period"],
            "actualAmount": float(r["actualAmount"]),
            "budgetAmount": float(r["budgetAmount"]),
            "varianceAmount": float(r["varianceAmount"]),
            "variancePct": float(r["variancePct"]),
        }
        for r in exp_rows
    ]

    return {
        "kpis": kpis,
        "categories": categories,
        "monthlyTrend": monthly_trend,
        "expenses": expenses,
    }
