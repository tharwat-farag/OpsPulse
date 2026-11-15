"""
Pytest configuration and synthetic fixtures for OpsPulse Data Quality tests.
Creates self-contained synthetic datasets that do not touch production data.
"""

import os
from typing import Dict
import pandas as pd
import pytest

# Ensure standard test database URL is available if not set in environment
if "OPSPULSE_DATABASE_URL" not in os.environ:
    os.environ["OPSPULSE_DATABASE_URL"] = (
        "postgresql+psycopg://retailflow_admin:111111@127.0.0.1:5432/opspulse_dw"
    )


@pytest.fixture
def valid_synthetic_datasets() -> Dict[str, pd.DataFrame]:
    """Generates a small valid synthetic dataset for all 12 OpsPulse Silver datasets."""
    products = pd.DataFrame([
        {
            "product_id": "P001",
            "product_name": "Pro Widget A",
            "category": "Electronics",
            "brand": "TechBrand",
            "standard_cost": 100.0,
            "current_selling_price": 150.0,
            "reorder_level": 10,
            "is_active": True,
            "standard_unit_margin": 50.0,
            "is_below_standard_cost": False,
        },
        {
            "product_id": "P002",
            "product_name": "Basic Widget B",
            "category": "Hardware",
            "brand": "BuildCorp",
            "standard_cost": 40.0,
            "current_selling_price": 60.0,
            "reorder_level": 5,
            "is_active": True,
            "standard_unit_margin": 20.0,
            "is_below_standard_cost": False,
        },
    ])

    customers = pd.DataFrame([
        {
            "customer_id": "C001",
            "customer_name": "Alice Smith",
            "customer_type": "Individual",
            "city": "Cairo",
            "registration_date": "2023-01-15",
            "customer_tenure_days": 1000,
        },
        {
            "customer_id": "C002",
            "customer_name": "Acme Retail Ltd",
            "customer_type": "Business",
            "city": "Alexandria",
            "registration_date": "2022-05-10",
            "customer_tenure_days": 1250,
        },
    ])

    branches = pd.DataFrame([
        {
            "branch_id": "B001",
            "branch_name": "Cairo Downtown",
            "city": "Cairo",
            "region": "Greater Cairo",
            "manager_name": "Tariq Mansour",
            "opening_date": "2020-01-01",
            "is_active": True,
            "branch_age_days": 2100,
        },
        {
            "branch_id": "B002",
            "branch_name": "Alex Corniche",
            "city": "Alexandria",
            "region": "Alexandria & Delta",
            "manager_name": "Nour Ibrahim",
            "opening_date": "2021-06-01",
            "is_active": True,
            "branch_age_days": 1600,
        },
    ])

    suppliers = pd.DataFrame([
        {
            "supplier_id": "S001",
            "supplier_name": "Global Tech Suppliers",
            "city": "Cairo",
            "contact_email": "info@globaltech.com",
            "rating": 4.5,
            "is_active": True,
            "is_low_rated": False,
            "rating_category": "Excellent",
        },
        {
            "supplier_id": "S002",
            "supplier_name": "Delta Parts Co",
            "city": "Alexandria",
            "contact_email": "orders@deltaparts.com",
            "rating": 3.8,
            "is_active": True,
            "is_low_rated": False,
            "rating_category": "Medium",
        },
    ])

    warehouses = pd.DataFrame([
        {
            "warehouse_id": "W001",
            "warehouse_name": "Cairo Central Depot",
            "city": "Cairo",
            "region": "Greater Cairo",
            "capacity_units": 5000,
            "is_active": True,
            "warehouse_location": "Cairo Industrial Zone",
            "warehouse_capacity_category": "Medium",
        },
    ])

    product_suppliers = pd.DataFrame([
        {
            "product_id": "P001",
            "supplier_id": "S001",
            "supplier_price": 95.0,
            "lead_time_days": 7,
            "minimum_order_qty": 5,
            "is_preferred_supplier": True,
            "supplier_cost_category": "Standard",
            "is_high_lead_time": False,
        },
        {
            "product_id": "P002",
            "supplier_id": "S002",
            "supplier_price": 38.0,
            "lead_time_days": 10,
            "minimum_order_qty": 10,
            "is_preferred_supplier": True,
            "supplier_cost_category": "Standard",
            "is_high_lead_time": False,
        },
    ])

    sales = pd.DataFrame([
        {
            "sales_line_id": "SL001",
            "invoice_id": "INV001",
            "sale_date": "2025-02-10",
            "product_id": "P001",
            "customer_id": "C001",
            "branch_id": "B001",
            "quantity": 2,
            "unit_price": 150.0,
            "unit_cost": 100.0,
            "discount_amount": 10.0,
            "gross_amount": 300.0,
            "net_revenue": 290.0,
            "total_cost": 200.0,
            "gross_profit": 90.0,
            "discount_rate": 0.0333,
            "is_loss_making": False,
            "sales_channel": "In-Store",
        },
    ])

    inventory = pd.DataFrame([
        {
            "inventory_snapshot_id": "IS001",
            "product_id": "P001",
            "warehouse_id": "W001",
            "snapshot_date": "2025-02-10",
            "quantity_on_hand": 50,
            "quantity_reserved": 5,
            "standard_cost": 100.0,
            "capacity_units": 5000,
            "available_quantity": 45,
            "is_stockout": False,
            "is_fully_reserved": False,
            "is_reserved_exceeds_on_hand": False,
            "total_inventory_value": 5000.0,
            "available_inventory_value": 4500.0,
            "reserved_inventory_value": 500.0,
            "warehouse_total_on_hand": 50,
            "capacity_utilization_pct": 1.0,
        },
    ])

    purchase_orders = pd.DataFrame([
        {
            "po_id": "PO001",
            "supplier_id": "S001",
            "order_date": "2025-01-10",
            "expected_delivery_date": "2025-01-20",
            "status": "Fully Received",
            "rejection_reason": None,
            "days_until_expected_delivery": 10,
            "is_cancelled": False,
            "is_pending": False,
            "is_fully_received": True,
            "is_partially_received": False,
        },
    ])

    purchase_order_lines = pd.DataFrame([
        {
            "po_line_id": "POL001",
            "po_id": "PO001",
            "product_id": "P001",
            "ordered_qty": 20,
            "unit_cost": 95.0,
            "rejection_reason": None,
            "line_total": 1900.0,
            "is_high_value_line": False,
        },
    ])

    goods_receipts = pd.DataFrame([
        {
            "receipt_id": "GR001",
            "po_line_id": "POL001",
            "received_date": "2025-01-18",
            "received_qty": 20,
            "accepted_qty": 20,
            "rejected_qty": 0,
            "po_id": "PO001",
            "order_date": "2025-01-10",
            "expected_delivery_date": "2025-01-20",
            "rejection_reason": None,
            "days_from_order": 8,
            "days_after_expected": -2,
            "is_late_receipt": False,
            "is_fully_accepted": True,
            "acceptance_rate": 1.0,
        },
    ])

    operating_expenses = pd.DataFrame([
        {
            "expense_id": "EX001",
            "branch_id": "B001",
            "expense_date": "2025-02-01",
            "expense_category": "Rent",
            "amount": 25000.0,
            "description": "Monthly branch rent",
            "expense_year": 2025,
            "expense_month": 2,
            "expense_quarter": "Q1",
        },
    ])

    return {
        "products": products,
        "customers": customers,
        "branches": branches,
        "suppliers": suppliers,
        "warehouses": warehouses,
        "product_suppliers": product_suppliers,
        "sales": sales,
        "inventory": inventory,
        "purchase_orders": purchase_orders,
        "purchase_order_lines": purchase_order_lines,
        "goods_receipts": goods_receipts,
        "operating_expenses": operating_expenses,
    }
