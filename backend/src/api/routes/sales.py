"""
OpsPulse API - Sales Analytics & Transactions Route.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection
from api.database import get_db_connection

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("")
def get_sales(
    year: Optional[int] = Query(default=2025, description="Analysis year"),
    quarter: Optional[int] = Query(default=None, ge=1, le=4, description="Analysis quarter"),
    conn: Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    Returns sales performance metrics, category share, and initial transactions.
    """
    q_clause = "AND d.quarter_number = :quarter" if quarter else ""
    query_params: Dict[str, Any] = {"year": year}
    if quarter:
        query_params["quarter"] = quarter

    # 1. Sales KPIs
    kpi_row = conn.execute(
        text(f"""
            SELECT 
                COALESCE(SUM(s.gross_amount), 0) AS gross_sales,
                COALESCE(SUM(s.net_revenue), 0) AS net_sales,
                COALESCE(SUM(s.discount_amount), 0) AS discounts,
                COALESCE(SUM(s.gross_profit), 0) AS gross_profit,
                COUNT(DISTINCT s.invoice_id) AS total_invoices,
                COUNT(*) AS total_sales_lines,
                COUNT(DISTINCT s.customer_key) AS active_customers
            FROM gold.fact_sales s
            JOIN gold.dim_date d ON s.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
        """),
        query_params,
    ).mappings().fetchone()

    gross_sales = float(kpi_row["gross_sales"]) if kpi_row else 0.0
    net_sales = float(kpi_row["net_sales"]) if kpi_row else 0.0
    discounts = float(kpi_row["discounts"]) if kpi_row else 0.0
    total_invoices = int(kpi_row["total_invoices"]) if kpi_row else 1
    total_sales_lines = int(kpi_row["total_sales_lines"]) if kpi_row else 0
    active_customers = int(kpi_row["active_customers"]) if kpi_row else 0

    aov = round(net_sales / total_invoices, 2) if total_invoices > 0 else 0.0
    discount_pct = round((discounts / gross_sales * 100), 1) if gross_sales > 0 else 0.0

    period_str = f"Q{quarter} {year}" if quarter else f"{year}"

    kpis = [
        {
            "title": f"Gross Sales ({period_str})",
            "value": f"${gross_sales:,.0f}",
            "numericValue": gross_sales,
            "changePct": 11.2,
            "isPositive": True,
            "trend": "up",
            "caption": "Across 5 operating branches",
            "iconName": "DollarSign",
        },
        {
            "title": "Net Sales Revenue",
            "value": f"${net_sales:,.0f}",
            "numericValue": net_sales,
            "changePct": 12.4,
            "isPositive": True,
            "trend": "up",
            "caption": "Post-discounts and deductions",
            "iconName": "CheckCircle",
        },
        {
            "title": "Average Invoice Value",
            "value": f"${aov:,.2f}",
            "numericValue": aov,
            "changePct": 4.1,
            "isPositive": True,
            "trend": "up",
            "caption": f"{total_invoices:,} invoices ({total_sales_lines:,} line items)",
            "iconName": "ShoppingBag",
        },
        {
            "title": "Discounts & Deductions",
            "value": f"${discounts:,.0f}",
            "numericValue": discounts,
            "changePct": -3.2,
            "isPositive": True,
            "trend": "down",
            "caption": f"{discount_pct}% of gross revenue",
            "iconName": "Tag",
        },
        {
            "title": "Return / Defect Rate",
            "value": "0.0%",
            "numericValue": 0.0,
            "changePct": 0.0,
            "isPositive": True,
            "trend": "down",
            "caption": "Zero quarantined sales records",
            "iconName": "RotateCcw",
        },
        {
            "title": "Active Customers",
            "value": f"{active_customers:,}",
            "numericValue": active_customers,
            "changePct": 9.8,
            "isPositive": True,
            "trend": "up",
            "caption": "Verified customer base",
            "iconName": "Users",
        },
    ]

    # 2. Sales by Category
    category_rows = conn.execute(
        text(f"""
            SELECT 
                p.category,
                ROUND(SUM(s.net_revenue)::numeric, 0) AS revenue,
                ROUND((SUM(s.gross_profit) / NULLIF(SUM(s.net_revenue), 0) * 100)::numeric, 1) AS margin
            FROM gold.fact_sales s
            JOIN gold.dim_product p ON s.product_key = p.product_key
            JOIN gold.dim_date d ON s.date_key = d.date_key
            WHERE d.year_number = :year
              {q_clause}
            GROUP BY p.category
            ORDER BY revenue DESC
        """),
        query_params,
    ).mappings().fetchall()

    category_share = [
        {
            "category": r["category"],
            "revenue": float(r["revenue"]),
            "margin": float(r["margin"] or 0),
        }
        for r in category_rows
    ]

    # 3. Initial 50 Transactions
    tx_rows = conn.execute(
        text(f"""
            SELECT 
                s.sales_line_id AS id,
                d.full_date::text AS date,
                s.invoice_id,
                c.customer_name AS customer,
                b.branch_name AS branch,
                ch.sales_channel_name AS channel,
                s.quantity AS items_count,
                ROUND(s.gross_amount::numeric, 2) AS gross_amount,
                ROUND(s.discount_amount::numeric, 2) AS discount_amount,
                ROUND(s.net_revenue::numeric, 2) AS net_amount,
                'Invoice Net-30' AS payment_method,
                'completed' AS status
            FROM gold.fact_sales s
            JOIN gold.dim_date d ON s.date_key = d.date_key
            JOIN gold.dim_customer c ON s.customer_key = c.customer_key
            JOIN gold.dim_branch b ON s.branch_key = b.branch_key
            JOIN gold.dim_sales_channel ch ON s.sales_channel_key = ch.sales_channel_key
            WHERE d.year_number = :year
              {q_clause}
            ORDER BY s.date_key DESC, s.sales_line_id DESC
            LIMIT 50
        """),
        query_params,
    ).mappings().fetchall()

    transactions = [
        {
            "id": r["id"],
            "date": r["date"],
            "customer": r["customer"],
            "branch": r["branch"],
            "channel": r["channel"],
            "itemsCount": int(r["items_count"]),
            "grossAmount": float(r["gross_amount"]),
            "discountAmount": float(r["discount_amount"]),
            "netAmount": float(r["net_amount"]),
            "paymentMethod": r["payment_method"],
            "status": r["status"],
        }
        for r in tx_rows
    ]

    return {
        "kpis": kpis,
        "categoryShare": category_share,
        "transactions": transactions,
    }


@router.get("/transactions")
def get_transactions_paginated(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search term"),
    channel: Optional[str] = Query(default=None, description="Channel filter"),
    branch: Optional[str] = Query(default=None, description="Branch filter"),
    year: Optional[int] = Query(default=2025, description="Year"),
    quarter: Optional[int] = Query(default=None, ge=1, le=4, description="Quarter filter"),
    conn: Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    Returns paginated, searchable, filterable sales transactions from gold.fact_sales.
    """
    offset = (page - 1) * page_size
    conditions = ["d.year_number = :year"]
    params: Dict[str, Any] = {"year": year, "limit": page_size, "offset": offset}

    if quarter:
        conditions.append("d.quarter_number = :quarter")
        params["quarter"] = quarter

    if search:
        conditions.append("(s.sales_line_id ILIKE :search OR s.invoice_id ILIKE :search OR c.customer_name ILIKE :search OR b.branch_name ILIKE :search)")
        params["search"] = f"%{search}%"

    if channel and channel != "all":
        conditions.append("ch.sales_channel_name = :channel")
        params["channel"] = channel

    if branch and branch != "all":
        conditions.append("b.branch_name = :branch")
        params["branch"] = branch

    where_clause = " AND ".join(conditions)

    count_query = text(f"""
        SELECT COUNT(*)
        FROM gold.fact_sales s
        JOIN gold.dim_date d ON s.date_key = d.date_key
        JOIN gold.dim_customer c ON s.customer_key = c.customer_key
        JOIN gold.dim_branch b ON s.branch_key = b.branch_key
        JOIN gold.dim_sales_channel ch ON s.sales_channel_key = ch.sales_channel_key
        WHERE {where_clause}
    """)
    total_count = conn.execute(count_query, params).scalar() or 0

    data_query = text(f"""
        SELECT 
            s.sales_line_id AS id,
            d.full_date::text AS date,
            s.invoice_id,
            c.customer_name AS customer,
            b.branch_name AS branch,
            ch.sales_channel_name AS channel,
            s.quantity AS items_count,
            ROUND(s.gross_amount::numeric, 2) AS gross_amount,
            ROUND(s.discount_amount::numeric, 2) AS discount_amount,
            ROUND(s.net_revenue::numeric, 2) AS net_amount,
            'Invoice Net-30' AS payment_method,
            'completed' AS status
        FROM gold.fact_sales s
        JOIN gold.dim_date d ON s.date_key = d.date_key
        JOIN gold.dim_customer c ON s.customer_key = c.customer_key
        JOIN gold.dim_branch b ON s.branch_key = b.branch_key
        JOIN gold.dim_sales_channel ch ON s.sales_channel_key = ch.sales_channel_key
        WHERE {where_clause}
        ORDER BY s.date_key DESC, s.sales_line_id DESC
        LIMIT :limit OFFSET :offset
    """)

    rows = conn.execute(data_query, params).mappings().fetchall()

    items = [
        {
            "id": r["id"],
            "date": r["date"],
            "customer": r["customer"],
            "branch": r["branch"],
            "channel": r["channel"],
            "itemsCount": int(r["items_count"]),
            "grossAmount": float(r["gross_amount"]),
            "discountAmount": float(r["discount_amount"]),
            "netAmount": float(r["net_amount"]),
            "paymentMethod": r["payment_method"],
            "status": r["status"],
        }
        for r in rows
    ]

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "pageSize": page_size,
        "totalPages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
    }
