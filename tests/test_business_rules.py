"""
Tests for Data Quality Business Rules module.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.business_rules import (
    check_goods_receipts_business_rules,
    check_inventory_business_rules,
    check_operating_expenses_business_rules,
    check_products_business_rules,
    check_purchase_order_lines_business_rules,
    check_purchase_orders_business_rules,
    check_sales_business_rules,
    check_suppliers_business_rules,
    check_warehouses_business_rules,
)
from validation.data_quality.models import CheckCategory, CheckStatus


def test_sales_business_rules_valid():
    df = pd.DataFrame([{
        "sales_line_id": "SL001",
        "quantity": 2,
        "unit_price": 50.0,
        "unit_cost": 30.0,
        "discount_amount": 5.0,
        "gross_amount": 100.0,
        "net_revenue": 95.0,
        "total_cost": 60.0,
        "gross_profit": 35.0,
    }])
    results = check_sales_business_rules(df, "test_batch_001")
    assert all(r.status == CheckStatus.PASSED.value for r in results)
    assert all(r.check_category == CheckCategory.BUSINESS_RULES.value for r in results)


def test_sales_business_rules_violations():
    df = pd.DataFrame([
        {
            "sales_line_id": "SL_BAD_1",
            "quantity": -2,           # negative quantity violation
            "unit_price": 50.0,
            "unit_cost": 30.0,
            "discount_amount": -5.0,  # negative discount violation
            "gross_amount": 100.0,
            "net_revenue": 50.0,      # net revenue calculation mismatch (100 - (-5) != 50)
            "total_cost": 60.0,
            "gross_profit": 35.0,
        }
    ])
    results = check_sales_business_rules(df, "test_batch_001")
    failures = [r for r in results if r.status == CheckStatus.FAILED.value]
    failure_names = {r.check_name for r in failures}
    assert "sales_positive_quantity" in failure_names
    assert "sales_discount_non_negative" in failure_names
    assert "sales_net_revenue_consistency" in failure_names


def test_inventory_business_rules_valid():
    df = pd.DataFrame([{
        "inventory_snapshot_id": "IS001",
        "quantity_on_hand": 10,
        "quantity_reserved": 2,
        "standard_cost": 15.0,
        "available_quantity": 8,
        "total_inventory_value": 150.0,
        "is_stockout": False,
    }])
    results = check_inventory_business_rules(df, "test_batch_001")
    assert all(r.status == CheckStatus.PASSED.value for r in results)


def test_inventory_business_rules_violations():
    df = pd.DataFrame([{
        "inventory_snapshot_id": "IS_BAD",
        "quantity_on_hand": 10,
        "quantity_reserved": 2,
        "standard_cost": 15.0,
        "available_quantity": 999,   # wrong available quantity (10 - 2 != 999)
        "total_inventory_value": 0.0, # wrong valuation
        "is_stockout": True,         # stockout is true despite on_hand == 10
    }])
    results = check_inventory_business_rules(df, "test_batch_001")
    failures = [r for r in results if r.status == CheckStatus.FAILED.value]
    failure_names = {r.check_name for r in failures}
    assert "inventory_available_quantity_consistency" in failure_names
    assert "inventory_total_value_consistency" in failure_names
    assert "inventory_stockout_flag_consistency" in failure_names


def test_purchase_orders_business_rules():
    df_valid = pd.DataFrame([{
        "po_id": "PO001",
        "order_date": "2025-01-01",
        "expected_delivery_date": "2025-01-05",
        "days_until_expected_delivery": 4,
    }])
    results_valid = check_purchase_orders_business_rules(df_valid, "batch_001")
    assert all(r.status == CheckStatus.PASSED.value for r in results_valid)

    df_invalid = pd.DataFrame([{
        "po_id": "PO002",
        "order_date": "2025-01-10",
        "expected_delivery_date": "2025-01-05",  # earlier than order date!
        "days_until_expected_delivery": 100,     # mismatch
    }])
    results_invalid = check_purchase_orders_business_rules(df_invalid, "batch_001")
    failures = [r for r in results_invalid if r.status == CheckStatus.FAILED.value]
    assert len(failures) == 2


def test_goods_receipts_quantity_balance():
    df_valid = pd.DataFrame([{
        "receipt_id": "GR001",
        "received_qty": 20,
        "accepted_qty": 18,
        "rejected_qty": 2,
        "order_date": "2025-01-01",
        "received_date": "2025-01-04",
        "acceptance_rate": 0.9,
    }])
    results_valid = check_goods_receipts_business_rules(df_valid, "batch_001")
    assert all(r.status == CheckStatus.PASSED.value for r in results_valid)

    df_invalid = pd.DataFrame([{
        "receipt_id": "GR002",
        "received_qty": 20,
        "accepted_qty": 10,
        "rejected_qty": 5,  # 10 + 5 != 20!
        "order_date": "2025-01-10",
        "received_date": "2025-01-02",  # received before order!
        "acceptance_rate": 0.5,
    }])
    results_invalid = check_goods_receipts_business_rules(df_invalid, "batch_001")
    failures = [r for r in results_invalid if r.status == CheckStatus.FAILED.value]
    failure_names = {r.check_name for r in failures}
    assert "gr_received_qty_balance" in failure_names
    assert "gr_received_date_after_order" in failure_names


def test_operating_expenses_business_rules():
    df_valid = pd.DataFrame([{
        "expense_id": "EX001",
        "expense_date": "2025-03-15",
        "expense_year": 2025,
        "expense_month": 3,
        "amount": 5000.0,
    }])
    results_valid = check_operating_expenses_business_rules(df_valid, "batch_001")
    assert all(r.status == CheckStatus.PASSED.value for r in results_valid)

    df_invalid = pd.DataFrame([{
        "expense_id": "EX002",
        "expense_date": "2025-03-15",
        "expense_year": 2024,   # mismatch
        "expense_month": 1,    # mismatch
        "amount": -500.0,      # negative expense amount!
    }])
    results_invalid = check_operating_expenses_business_rules(df_invalid, "batch_001")
    failures = [r for r in results_invalid if r.status == CheckStatus.FAILED.value]
    failure_names = {r.check_name for r in failures}
    assert "expense_amount_positive" in failure_names
    assert "expense_date_parts_consistency" in failure_names
