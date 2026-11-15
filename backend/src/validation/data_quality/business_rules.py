"""
OpsPulse Data Quality Framework - Business Rules Validation.

Implements business logic validations derived from the OpsPulse data model:
- Sales pricing, gross amounts, discounts, net revenues, costs, profits
- Inventory on hand, reserved quantities, available stock, valuations, stockout flags
- Purchase order timeline and scheduling consistency
- Purchase order lines calculation consistency
- Goods receipts quantity balancing and timeline consistency
- Operating expense amount positive constraints
- Product margins, price thresholds, and cost non-negativity
- Supplier ratings and warehouse capacities
"""

from typing import Any, Callable, List, Optional
import numpy as np
import pandas as pd

from .models import CheckCategory, CheckResult, CheckSeverity


def check_custom_rule(
    df: pd.DataFrame,
    dataset: str,
    check_name: str,
    condition_fn: Callable[[pd.DataFrame], pd.Series],
    batch_id: str,
    id_column: Optional[str] = None,
    details_desc: str = "",
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Evaluates an arbitrary business rule condition over a dataframe.
    condition_fn(df) should return a boolean pd.Series where True indicates COMPLIANCE
    and False indicates a VIOLATION.
    """
    total_records = len(df)

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.BUSINESS_RULES,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no records to evaluate for {check_name}.",
        )

    try:
        compliance_series = condition_fn(df)
        violation_mask = ~compliance_series
        failed_count = int(violation_mask.sum())
    except Exception as exc:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.BUSINESS_RULES,
            total_records=total_records,
            failed_records=total_records,
            batch_id=batch_id,
            severity=severity,
            details=f"Execution error evaluating rule '{check_name}': {exc}",
        )

    sample_failures: List[Any] = []
    if failed_count > 0:
        if id_column and id_column in df.columns:
            sample_failures = (
                df.loc[violation_mask, id_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_failures = df[violation_mask].index[:10].tolist()

        fail_pct = round((failed_count / total_records) * 100.0, 2)
        details = (
            f"Rule violation: {failed_count} records ({fail_pct}%) failed '{check_name}'. "
            f"{details_desc}"
        )
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.BUSINESS_RULES,
            total_records=total_records,
            failed_records=failed_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_failures,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=check_name,
        category=CheckCategory.BUSINESS_RULES,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"All {total_records:,} records conform to rule: {details_desc or check_name}.",
    )


# ==============================================================================
# SALES BUSINESS RULES
# ==============================================================================

def check_sales_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver sales records."""
    results: List[CheckResult] = []

    # 1. Sales quantity must be positive
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_positive_quantity",
            condition_fn=lambda d: pd.to_numeric(d["quantity"], errors="coerce") > 0,
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Sales quantity must be strictly greater than 0.",
        )
    )

    # 2. Unit price and unit cost non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_unit_price_cost_non_negative",
            condition_fn=lambda d: (
                (pd.to_numeric(d["unit_price"], errors="coerce") >= 0)
                & (pd.to_numeric(d["unit_cost"], errors="coerce") >= 0)
            ),
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Unit price and unit cost must be non-negative (>= 0).",
        )
    )

    # 3. Discounts must not be negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_discount_non_negative",
            condition_fn=lambda d: pd.to_numeric(d["discount_amount"], errors="coerce") >= 0,
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Discount amount cannot be negative (>= 0).",
        )
    )

    # 4. Gross amount consistency: gross_amount == quantity * unit_price
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_gross_amount_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["gross_amount"], errors="coerce"),
                pd.to_numeric(d["quantity"], errors="coerce") * pd.to_numeric(d["unit_price"], errors="coerce"),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Gross amount must equal quantity * unit_price (tolerance 0.05).",
        )
    )

    # 5. Net revenue consistency: net_revenue == gross_amount - discount_amount
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_net_revenue_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["net_revenue"], errors="coerce"),
                pd.to_numeric(d["gross_amount"], errors="coerce") - pd.to_numeric(d["discount_amount"], errors="coerce"),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Net revenue must equal gross_amount - discount_amount (tolerance 0.05).",
        )
    )

    # 6. Total cost consistency: total_cost == quantity * unit_cost
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_total_cost_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["total_cost"], errors="coerce"),
                pd.to_numeric(d["quantity"], errors="coerce") * pd.to_numeric(d["unit_cost"], errors="coerce"),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Total cost must equal quantity * unit_cost (tolerance 0.05).",
        )
    )

    # 7. Gross profit consistency: gross_profit == net_revenue - total_cost
    results.append(
        check_custom_rule(
            df=df,
            dataset="sales",
            check_name="sales_gross_profit_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["gross_profit"], errors="coerce"),
                pd.to_numeric(d["net_revenue"], errors="coerce") - pd.to_numeric(d["total_cost"], errors="coerce"),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="sales_line_id",
            details_desc="Gross profit must equal net_revenue - total_cost (tolerance 0.05).",
        )
    )

    return results


# ==============================================================================
# INVENTORY BUSINESS RULES
# ==============================================================================

def check_inventory_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver inventory records."""
    results: List[CheckResult] = []

    # 1. Quantities non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="inventory",
            check_name="inventory_quantities_non_negative",
            condition_fn=lambda d: (
                (pd.to_numeric(d["quantity_on_hand"], errors="coerce") >= 0)
                & (pd.to_numeric(d["quantity_reserved"], errors="coerce") >= 0)
            ),
            batch_id=batch_id,
            id_column="inventory_snapshot_id",
            details_desc="Quantity on hand and reserved quantity must be non-negative (>= 0).",
        )
    )

    # 2. Available quantity consistency: available_quantity == quantity_on_hand - quantity_reserved
    results.append(
        check_custom_rule(
            df=df,
            dataset="inventory",
            check_name="inventory_available_quantity_consistency",
            condition_fn=lambda d: (
                pd.to_numeric(d["available_quantity"], errors="coerce")
                == (pd.to_numeric(d["quantity_on_hand"], errors="coerce") - pd.to_numeric(d["quantity_reserved"], errors="coerce"))
            ),
            batch_id=batch_id,
            id_column="inventory_snapshot_id",
            details_desc="Available quantity must equal on_hand - reserved.",
        )
    )

    # 3. Total inventory value consistency: total_inventory_value == round(quantity_on_hand * standard_cost, 2)
    results.append(
        check_custom_rule(
            df=df,
            dataset="inventory",
            check_name="inventory_total_value_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["total_inventory_value"], errors="coerce"),
                np.round(
                    pd.to_numeric(d["quantity_on_hand"], errors="coerce") * pd.to_numeric(d["standard_cost"], errors="coerce"),
                    2,
                ),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="inventory_snapshot_id",
            details_desc="Total inventory value must match quantity_on_hand * standard_cost (tolerance 0.05).",
        )
    )

    # 4. Stockout flag consistency: is_stockout == (quantity_on_hand == 0)
    results.append(
        check_custom_rule(
            df=df,
            dataset="inventory",
            check_name="inventory_stockout_flag_consistency",
            condition_fn=lambda d: (
                d["is_stockout"].astype(bool)
                == (pd.to_numeric(d["quantity_on_hand"], errors="coerce") == 0)
            ),
            batch_id=batch_id,
            id_column="inventory_snapshot_id",
            details_desc="is_stockout flag must be True if and only if quantity_on_hand is 0.",
        )
    )

    return results


# ==============================================================================
# PURCHASE ORDERS & LINES BUSINESS RULES
# ==============================================================================

def check_purchase_orders_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver purchase_orders records."""
    results: List[CheckResult] = []

    # 1. Expected delivery date >= order date
    results.append(
        check_custom_rule(
            df=df,
            dataset="purchase_orders",
            check_name="po_delivery_date_chronological",
            condition_fn=lambda d: pd.to_datetime(d["expected_delivery_date"]) >= pd.to_datetime(d["order_date"]),
            batch_id=batch_id,
            id_column="po_id",
            details_desc="Expected delivery date must be on or after order date.",
        )
    )

    # 2. Days until expected delivery calculation consistency
    results.append(
        check_custom_rule(
            df=df,
            dataset="purchase_orders",
            check_name="po_days_until_delivery_consistency",
            condition_fn=lambda d: (
                pd.to_numeric(d["days_until_expected_delivery"], errors="coerce")
                == (pd.to_datetime(d["expected_delivery_date"]) - pd.to_datetime(d["order_date"])).dt.days
            ),
            batch_id=batch_id,
            id_column="po_id",
            details_desc="days_until_expected_delivery must equal difference between expected delivery and order date.",
        )
    )

    return results


def check_purchase_order_lines_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver purchase_order_lines records."""
    results: List[CheckResult] = []

    # 1. Ordered quantity must be positive
    results.append(
        check_custom_rule(
            df=df,
            dataset="purchase_order_lines",
            check_name="po_lines_positive_ordered_qty",
            condition_fn=lambda d: pd.to_numeric(d["ordered_qty"], errors="coerce") > 0,
            batch_id=batch_id,
            id_column="po_line_id",
            details_desc="Ordered quantity must be greater than zero.",
        )
    )

    # 2. Unit cost non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="purchase_order_lines",
            check_name="po_lines_non_negative_unit_cost",
            condition_fn=lambda d: pd.to_numeric(d["unit_cost"], errors="coerce") >= 0,
            batch_id=batch_id,
            id_column="po_line_id",
            details_desc="Unit cost must be non-negative (>= 0).",
        )
    )

    # 3. Line total consistency: line_total == round(ordered_qty * unit_cost, 2)
    results.append(
        check_custom_rule(
            df=df,
            dataset="purchase_order_lines",
            check_name="po_lines_line_total_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["line_total"], errors="coerce"),
                np.round(
                    pd.to_numeric(d["ordered_qty"], errors="coerce") * pd.to_numeric(d["unit_cost"], errors="coerce"),
                    2,
                ),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="po_line_id",
            details_desc="Line total must equal ordered_qty * unit_cost (tolerance 0.05).",
        )
    )

    return results


# ==============================================================================
# GOODS RECEIPTS BUSINESS RULES
# ==============================================================================

def check_goods_receipts_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver goods_receipts records."""
    results: List[CheckResult] = []

    # 1. Received quantity balance: received_qty == accepted_qty + rejected_qty
    results.append(
        check_custom_rule(
            df=df,
            dataset="goods_receipts",
            check_name="gr_received_qty_balance",
            condition_fn=lambda d: (
                pd.to_numeric(d["received_qty"], errors="coerce")
                == (pd.to_numeric(d["accepted_qty"], errors="coerce") + pd.to_numeric(d["rejected_qty"], errors="coerce"))
            ),
            batch_id=batch_id,
            id_column="receipt_id",
            details_desc="Received quantity must equal accepted_qty + rejected_qty.",
        )
    )

    # 2. Quantities non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="goods_receipts",
            check_name="gr_quantities_non_negative",
            condition_fn=lambda d: (
                (pd.to_numeric(d["received_qty"], errors="coerce") >= 0)
                & (pd.to_numeric(d["accepted_qty"], errors="coerce") >= 0)
                & (pd.to_numeric(d["rejected_qty"], errors="coerce") >= 0)
            ),
            batch_id=batch_id,
            id_column="receipt_id",
            details_desc="Received, accepted, and rejected quantities must be non-negative.",
        )
    )

    # 3. Received date >= order date
    results.append(
        check_custom_rule(
            df=df,
            dataset="goods_receipts",
            check_name="gr_received_date_after_order",
            condition_fn=lambda d: pd.to_datetime(d["received_date"]) >= pd.to_datetime(d["order_date"]),
            batch_id=batch_id,
            id_column="receipt_id",
            details_desc="Goods receipt received_date must be on or after order_date.",
        )
    )

    # 4. Acceptance rate consistency: acceptance_rate == accepted_qty / received_qty
    def _check_acceptance_rate(d: pd.DataFrame) -> pd.Series:
        recv = pd.to_numeric(d["received_qty"], errors="coerce")
        acc = pd.to_numeric(d["accepted_qty"], errors="coerce")
        rate = pd.to_numeric(d["acceptance_rate"], errors="coerce")
        # Where received > 0, rate should match accepted / received
        valid_pos = (recv > 0) & np.isclose(rate, acc / recv, atol=0.01)
        # Where received == 0, rate is typically 0 or 1
        valid_zero = (recv == 0) & (rate >= 0) & (rate <= 1)
        return valid_pos | valid_zero

    results.append(
        check_custom_rule(
            df=df,
            dataset="goods_receipts",
            check_name="gr_acceptance_rate_consistency",
            condition_fn=_check_acceptance_rate,
            batch_id=batch_id,
            id_column="receipt_id",
            details_desc="Acceptance rate must equal accepted_qty / received_qty (tolerance 0.01).",
        )
    )

    return results


# ==============================================================================
# OPERATING EXPENSES BUSINESS RULES
# ==============================================================================

def check_operating_expenses_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver operating_expenses records."""
    results: List[CheckResult] = []

    # 1. Expense amount must be strictly positive
    results.append(
        check_custom_rule(
            df=df,
            dataset="operating_expenses",
            check_name="expense_amount_positive",
            condition_fn=lambda d: pd.to_numeric(d["amount"], errors="coerce") > 0,
            batch_id=batch_id,
            id_column="expense_id",
            details_desc="Operating expense amount must be greater than zero.",
        )
    )

    # 2. Date year and month alignment
    results.append(
        check_custom_rule(
            df=df,
            dataset="operating_expenses",
            check_name="expense_date_parts_consistency",
            condition_fn=lambda d: (
                (pd.to_datetime(d["expense_date"]).dt.year == pd.to_numeric(d["expense_year"], errors="coerce"))
                & (pd.to_datetime(d["expense_date"]).dt.month == pd.to_numeric(d["expense_month"], errors="coerce"))
            ),
            batch_id=batch_id,
            id_column="expense_id",
            details_desc="expense_year and expense_month must match expense_date.",
        )
    )

    return results


# ==============================================================================
# PRODUCTS, SUPPLIERS, WAREHOUSES BUSINESS RULES
# ==============================================================================

def check_products_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver products records."""
    results: List[CheckResult] = []

    # 1. Costs and prices non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="products",
            check_name="products_cost_price_non_negative",
            condition_fn=lambda d: (
                (pd.to_numeric(d["standard_cost"], errors="coerce") >= 0)
                & (pd.to_numeric(d["current_selling_price"], errors="coerce") >= 0)
                & (pd.to_numeric(d["reorder_level"], errors="coerce") >= 0)
            ),
            batch_id=batch_id,
            id_column="product_id",
            details_desc="Standard cost, selling price, and reorder level must be non-negative.",
        )
    )

    # 2. Standard unit margin: standard_unit_margin == current_selling_price - standard_cost
    results.append(
        check_custom_rule(
            df=df,
            dataset="products",
            check_name="products_unit_margin_consistency",
            condition_fn=lambda d: np.isclose(
                pd.to_numeric(d["standard_unit_margin"], errors="coerce"),
                pd.to_numeric(d["current_selling_price"], errors="coerce") - pd.to_numeric(d["standard_cost"], errors="coerce"),
                atol=0.05,
            ),
            batch_id=batch_id,
            id_column="product_id",
            details_desc="Standard unit margin must equal current_selling_price - standard_cost.",
        )
    )

    return results


def check_suppliers_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver suppliers records."""
    results: List[CheckResult] = []

    # 1. Rating between 0 and 5
    results.append(
        check_custom_rule(
            df=df,
            dataset="suppliers",
            check_name="suppliers_rating_range",
            condition_fn=lambda d: (
                (pd.to_numeric(d["rating"], errors="coerce") >= 0.0)
                & (pd.to_numeric(d["rating"], errors="coerce") <= 5.0)
            ),
            batch_id=batch_id,
            id_column="supplier_id",
            details_desc="Supplier rating must be between 0.0 and 5.0.",
        )
    )

    return results


def check_warehouses_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver warehouses records."""
    results: List[CheckResult] = []

    # 1. Capacity units must be positive
    results.append(
        check_custom_rule(
            df=df,
            dataset="warehouses",
            check_name="warehouses_capacity_positive",
            condition_fn=lambda d: pd.to_numeric(d["capacity_units"], errors="coerce") > 0,
            batch_id=batch_id,
            id_column="warehouse_id",
            details_desc="Warehouse capacity units must be strictly positive (> 0).",
        )
    )

    return results


def check_product_suppliers_business_rules(df: pd.DataFrame, batch_id: str) -> List[CheckResult]:
    """Evaluates business rules for Silver product_suppliers records."""
    results: List[CheckResult] = []

    # 1. Price non-negative, MOQ positive, lead time non-negative
    results.append(
        check_custom_rule(
            df=df,
            dataset="product_suppliers",
            check_name="product_suppliers_price_and_lead_time_valid",
            condition_fn=lambda d: (
                (pd.to_numeric(d["supplier_price"], errors="coerce") >= 0)
                & (pd.to_numeric(d["lead_time_days"], errors="coerce") >= 0)
                & (pd.to_numeric(d["minimum_order_qty"], errors="coerce") > 0)
            ),
            batch_id=batch_id,
            id_column="product_id",
            details_desc="supplier_price >= 0, lead_time_days >= 0, and minimum_order_qty > 0.",
        )
    )

    return results
