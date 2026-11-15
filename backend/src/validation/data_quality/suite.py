"""
OpsPulse Data Quality Framework - Quality Suite Orchestrator.

Orchestrates all Completeness, Uniqueness, Referential Integrity,
Business Rules, and Validity checks across the 12 OpsPulse Silver datasets.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from .models import (
    BatchQualityReport,
    CheckCategory,
    CheckResult,
    CheckSeverity,
    CheckStatus,
    DatasetQualitySummary,
)
from .completeness import check_dataset_completeness
from .uniqueness import check_uniqueness
from .referential import check_foreign_key
from .validity import (
    check_accepted_values,
    check_date_validity,
    check_numeric_range,
)
from .business_rules import (
    check_goods_receipts_business_rules,
    check_inventory_business_rules,
    check_operating_expenses_business_rules,
    check_product_suppliers_business_rules,
    check_products_business_rules,
    check_purchase_order_lines_business_rules,
    check_purchase_orders_business_rules,
    check_sales_business_rules,
    check_suppliers_business_rules,
    check_warehouses_business_rules,
)

DATASETS = [
    "products",
    "customers",
    "branches",
    "suppliers",
    "warehouses",
    "product_suppliers",
    "sales",
    "inventory",
    "purchase_orders",
    "purchase_order_lines",
    "goods_receipts",
    "operating_expenses",
]

# Dataset Schemas and Critical Columns Configuration
DATASET_CONFIG: Dict[str, Dict] = {
    "products": {
        "id_column": "product_id",
        "pk": "product_id",
        "required_columns": [
            "product_id", "product_name", "category", "brand",
            "standard_cost", "current_selling_price", "reorder_level",
            "is_active", "standard_unit_margin", "is_below_standard_cost"
        ],
        "critical_columns": ["product_id", "standard_cost", "current_selling_price"],
        "allow_null_columns": set(),
    },
    "customers": {
        "id_column": "customer_id",
        "pk": "customer_id",
        "required_columns": [
            "customer_id", "customer_name", "customer_type", "city",
            "registration_date", "customer_tenure_days"
        ],
        "critical_columns": ["customer_id", "customer_type", "registration_date"],
        "allow_null_columns": set(),
    },
    "branches": {
        "id_column": "branch_id",
        "pk": "branch_id",
        "required_columns": [
            "branch_id", "branch_name", "city", "region",
            "manager_name", "opening_date", "is_active", "branch_age_days"
        ],
        "critical_columns": ["branch_id", "branch_name", "city"],
        "allow_null_columns": set(),
    },
    "suppliers": {
        "id_column": "supplier_id",
        "pk": "supplier_id",
        "required_columns": [
            "supplier_id", "supplier_name", "city", "contact_email",
            "rating", "is_active", "is_low_rated", "rating_category"
        ],
        "critical_columns": ["supplier_id", "supplier_name", "rating"],
        "allow_null_columns": set(),
    },
    "warehouses": {
        "id_column": "warehouse_id",
        "pk": "warehouse_id",
        "required_columns": [
            "warehouse_id", "warehouse_name", "city", "region",
            "capacity_units", "is_active", "warehouse_location", "warehouse_capacity_category"
        ],
        "critical_columns": ["warehouse_id", "capacity_units"],
        "allow_null_columns": set(),
    },
    "product_suppliers": {
        "id_column": "product_id",
        "pk": ["product_id", "supplier_id"],
        "required_columns": [
            "product_id", "supplier_id", "supplier_price", "lead_time_days",
            "minimum_order_qty", "is_preferred_supplier", "supplier_cost_category", "is_high_lead_time"
        ],
        "critical_columns": ["product_id", "supplier_id", "supplier_price"],
        "allow_null_columns": set(),
    },
    "sales": {
        "id_column": "sales_line_id",
        "pk": "sales_line_id",
        "required_columns": [
            "sales_line_id", "invoice_id", "sale_date", "product_id", "customer_id",
            "branch_id", "quantity", "unit_price", "unit_cost", "discount_amount",
            "gross_amount", "net_revenue", "total_cost", "gross_profit",
            "discount_rate", "is_loss_making", "sales_channel"
        ],
        "critical_columns": [
            "sales_line_id", "sale_date", "product_id", "customer_id",
            "branch_id", "quantity", "unit_price", "net_revenue"
        ],
        "allow_null_columns": set(),
    },
    "inventory": {
        "id_column": "inventory_snapshot_id",
        "pk": "inventory_snapshot_id",
        "business_key": ["product_id", "warehouse_id", "snapshot_date"],
        "required_columns": [
            "inventory_snapshot_id", "product_id", "warehouse_id", "snapshot_date",
            "quantity_on_hand", "quantity_reserved", "standard_cost", "capacity_units",
            "available_quantity", "is_stockout", "is_fully_reserved", "is_reserved_exceeds_on_hand",
            "total_inventory_value", "available_inventory_value", "reserved_inventory_value",
            "warehouse_total_on_hand", "capacity_utilization_pct"
        ],
        "critical_columns": [
            "inventory_snapshot_id", "product_id", "warehouse_id",
            "snapshot_date", "quantity_on_hand"
        ],
        "allow_null_columns": set(),
    },
    "purchase_orders": {
        "id_column": "po_id",
        "pk": "po_id",
        "required_columns": [
            "po_id", "supplier_id", "order_date", "expected_delivery_date",
            "status", "rejection_reason", "days_until_expected_delivery",
            "is_cancelled", "is_pending", "is_fully_received", "is_partially_received"
        ],
        "critical_columns": ["po_id", "supplier_id", "order_date", "status"],
        "allow_null_columns": {"rejection_reason"},
    },
    "purchase_order_lines": {
        "id_column": "po_line_id",
        "pk": "po_line_id",
        "required_columns": [
            "po_line_id", "po_id", "product_id", "ordered_qty", "unit_cost",
            "rejection_reason", "line_total", "is_high_value_line"
        ],
        "critical_columns": ["po_line_id", "po_id", "product_id", "ordered_qty", "unit_cost"],
        "allow_null_columns": {"rejection_reason"},
    },
    "goods_receipts": {
        "id_column": "receipt_id",
        "pk": "receipt_id",
        "required_columns": [
            "receipt_id", "po_line_id", "received_date", "received_qty",
            "accepted_qty", "rejected_qty", "po_id", "order_date",
            "expected_delivery_date", "rejection_reason", "days_from_order",
            "days_after_expected", "is_late_receipt", "is_fully_accepted", "acceptance_rate"
        ],
        "critical_columns": ["receipt_id", "po_line_id", "po_id", "received_date", "received_qty"],
        "allow_null_columns": {"rejection_reason"},
    },
    "operating_expenses": {
        "id_column": "expense_id",
        "pk": "expense_id",
        "required_columns": [
            "expense_id", "branch_id", "expense_date", "expense_category",
            "amount", "description", "expense_year", "expense_month", "expense_quarter"
        ],
        "critical_columns": ["expense_id", "branch_id", "expense_date", "expense_category", "amount"],
        "allow_null_columns": set(),
    },
}


class QualitySuite:
    """
    Executes all configured data quality checks across datasets.
    Can be run against a batch directory or an in-memory dictionary of DataFrames.
    """

    def __init__(self, batch_id: str, datasets_data: Optional[Dict[str, pd.DataFrame]] = None):
        self.batch_id = batch_id
        self.datasets: Dict[str, pd.DataFrame] = datasets_data or {}

    @classmethod
    def from_batch_directory(cls, batch_id: str, silver_dir: Path) -> "QualitySuite":
        """Loads all Silver CSVs from the batch directory."""
        batch_path = silver_dir / batch_id
        if not batch_path.exists():
            raise FileNotFoundError(f"Silver batch directory not found: {batch_path}")

        loaded: Dict[str, pd.DataFrame] = {}
        for d in DATASETS:
            csv_path = batch_path / f"{d}.csv"
            if csv_path.exists():
                loaded[d] = pd.read_csv(csv_path)
            else:
                # If file missing, represent as empty DataFrame with no columns
                loaded[d] = pd.DataFrame()

        return cls(batch_id=batch_id, datasets_data=loaded)

    def run(self) -> BatchQualityReport:
        """Runs the complete suite and compiles the BatchQualityReport."""
        execution_ts = datetime.now(timezone.utc).isoformat()
        all_results: List[CheckResult] = []

        # Run per-dataset checks
        for d in DATASETS:
            df = self.datasets.get(d, pd.DataFrame())
            cfg = DATASET_CONFIG[d]

            # 1. Completeness Checks
            comp_results = check_dataset_completeness(
                df=df,
                dataset=d,
                required_columns=cfg["required_columns"],
                critical_columns=cfg["critical_columns"],
                batch_id=self.batch_id,
                id_column=cfg["id_column"],
                allow_null_columns=cfg["allow_null_columns"],
            )
            all_results.extend(comp_results)

            # 2. Uniqueness Checks
            pk = cfg["pk"]
            all_results.append(
                check_uniqueness(
                    df=df,
                    dataset=d,
                    key_columns=pk,
                    batch_id=self.batch_id,
                    check_name_suffix="primary_key",
                )
            )

            # Additional business key uniqueness if configured
            if "business_key" in cfg:
                all_results.append(
                    check_uniqueness(
                        df=df,
                        dataset=d,
                        key_columns=cfg["business_key"],
                        batch_id=self.batch_id,
                        check_name_suffix="business_key",
                    )
                )

            # 3. Validity Checks (per dataset specifics)
            validity_results = self._run_validity_checks(d, df)
            all_results.extend(validity_results)

            # 4. Business Rules Checks (per dataset specifics)
            biz_results = self._run_business_rules(d, df)
            all_results.extend(biz_results)

        # 5. Referential Integrity Checks (Cross-dataset)
        ref_results = self._run_referential_checks()
        all_results.extend(ref_results)

        # Compile summaries and report
        return self._compile_report(all_results, execution_ts)

    def _run_validity_checks(self, dataset: str, df: pd.DataFrame) -> List[CheckResult]:
        """Runs validity checks tailored to each dataset."""
        res: List[CheckResult] = []
        batch = self.batch_id

        if dataset == "products":
            res.append(check_numeric_range(df, "products", "standard_cost", batch, min_value=0.0))
            res.append(check_numeric_range(df, "products", "current_selling_price", batch, min_value=0.0))

        elif dataset == "customers":
            res.append(check_accepted_values(df, "customers", "customer_type", ["Individual", "Business"], batch))
            res.append(check_date_validity(df, "customers", "registration_date", batch, id_column="customer_id"))

        elif dataset == "branches":
            res.append(check_date_validity(df, "branches", "opening_date", batch, id_column="branch_id"))
            res.append(check_numeric_range(df, "branches", "branch_age_days", batch, min_value=0.0))

        elif dataset == "suppliers":
            res.append(check_numeric_range(df, "suppliers", "rating", batch, min_value=0.0, max_value=5.0))
            res.append(check_accepted_values(df, "suppliers", "rating_category", ["Low", "Medium", "Good", "Excellent"], batch))

        elif dataset == "warehouses":
            res.append(check_numeric_range(df, "warehouses", "capacity_units", batch, min_value=1.0))
            res.append(check_accepted_values(df, "warehouses", "warehouse_capacity_category", ["Small", "Medium", "Large"], batch))

        elif dataset == "sales":
            res.append(check_accepted_values(df, "sales", "sales_channel", ["In-Store", "Online", "Phone"], batch))
            res.append(check_date_validity(df, "sales", "sale_date", batch, id_column="sales_line_id"))

        elif dataset == "inventory":
            res.append(check_date_validity(df, "inventory", "snapshot_date", batch, id_column="inventory_snapshot_id"))

        elif dataset == "purchase_orders":
            res.append(check_accepted_values(
                df, "purchase_orders", "status",
                ["Pending", "Partially Received", "Fully Received", "Cancelled"],
                batch,
            ))
            res.append(check_date_validity(df, "purchase_orders", "order_date", batch, id_column="po_id"))
            res.append(check_date_validity(df, "purchase_orders", "expected_delivery_date", batch, id_column="po_id"))

        elif dataset == "purchase_order_lines":
            res.append(check_numeric_range(df, "purchase_order_lines", "ordered_qty", batch, min_value=1.0))
            res.append(check_numeric_range(df, "purchase_order_lines", "unit_cost", batch, min_value=0.0))

        elif dataset == "goods_receipts":
            res.append(check_date_validity(df, "goods_receipts", "received_date", batch, id_column="receipt_id"))
            res.append(check_numeric_range(df, "goods_receipts", "acceptance_rate", batch, min_value=0.0, max_value=1.0))

        elif dataset == "operating_expenses":
            res.append(check_date_validity(df, "operating_expenses", "expense_date", batch, id_column="expense_id"))
            res.append(check_accepted_values(
                df, "operating_expenses", "expense_quarter",
                ["Q1", "Q2", "Q3", "Q4"],
                batch,
            ))
            res.append(check_accepted_values(
                df, "operating_expenses", "expense_category",
                ["Rent", "Salaries", "Utilities", "Marketing", "Logistics", "Maintenance", "Electricity", "Transportation", "Insurance", "Miscellaneous"],
                batch,
            ))

        return res

    def _run_business_rules(self, dataset: str, df: pd.DataFrame) -> List[CheckResult]:
        """Runs domain business rules tailored to each dataset."""
        batch = self.batch_id
        if dataset == "products":
            return check_products_business_rules(df, batch)
        elif dataset == "suppliers":
            return check_suppliers_business_rules(df, batch)
        elif dataset == "warehouses":
            return check_warehouses_business_rules(df, batch)
        elif dataset == "product_suppliers":
            return check_product_suppliers_business_rules(df, batch)
        elif dataset == "sales":
            return check_sales_business_rules(df, batch)
        elif dataset == "inventory":
            return check_inventory_business_rules(df, batch)
        elif dataset == "purchase_orders":
            return check_purchase_orders_business_rules(df, batch)
        elif dataset == "purchase_order_lines":
            return check_purchase_order_lines_business_rules(df, batch)
        elif dataset == "goods_receipts":
            return check_goods_receipts_business_rules(df, batch)
        elif dataset == "operating_expenses":
            return check_operating_expenses_business_rules(df, batch)
        return []

    def _run_referential_checks(self) -> List[CheckResult]:
        """Runs cross-dataset foreign key validations based on OpsPulse schema model."""
        res: List[CheckResult] = []
        b = self.batch_id
        d = self.datasets

        # 1. product_suppliers -> products, suppliers
        res.append(check_foreign_key(d.get("product_suppliers", pd.DataFrame()), "product_suppliers", "product_id", d.get("products", pd.DataFrame()), "products", "product_id", b))
        res.append(check_foreign_key(d.get("product_suppliers", pd.DataFrame()), "product_suppliers", "supplier_id", d.get("suppliers", pd.DataFrame()), "suppliers", "supplier_id", b))

        # 2. sales -> products, customers, branches
        res.append(check_foreign_key(d.get("sales", pd.DataFrame()), "sales", "product_id", d.get("products", pd.DataFrame()), "products", "product_id", b, child_id_column="sales_line_id"))
        res.append(check_foreign_key(d.get("sales", pd.DataFrame()), "sales", "customer_id", d.get("customers", pd.DataFrame()), "customers", "customer_id", b, child_id_column="sales_line_id"))
        res.append(check_foreign_key(d.get("sales", pd.DataFrame()), "sales", "branch_id", d.get("branches", pd.DataFrame()), "branches", "branch_id", b, child_id_column="sales_line_id"))

        # 3. inventory -> products, warehouses
        res.append(check_foreign_key(d.get("inventory", pd.DataFrame()), "inventory", "product_id", d.get("products", pd.DataFrame()), "products", "product_id", b, child_id_column="inventory_snapshot_id"))
        res.append(check_foreign_key(d.get("inventory", pd.DataFrame()), "inventory", "warehouse_id", d.get("warehouses", pd.DataFrame()), "warehouses", "warehouse_id", b, child_id_column="inventory_snapshot_id"))

        # 4. purchase_orders -> suppliers
        res.append(check_foreign_key(d.get("purchase_orders", pd.DataFrame()), "purchase_orders", "supplier_id", d.get("suppliers", pd.DataFrame()), "suppliers", "supplier_id", b, child_id_column="po_id"))

        # 5. purchase_order_lines -> purchase_orders, products
        res.append(check_foreign_key(d.get("purchase_order_lines", pd.DataFrame()), "purchase_order_lines", "po_id", d.get("purchase_orders", pd.DataFrame()), "purchase_orders", "po_id", b, child_id_column="po_line_id"))
        res.append(check_foreign_key(d.get("purchase_order_lines", pd.DataFrame()), "purchase_order_lines", "product_id", d.get("products", pd.DataFrame()), "products", "product_id", b, child_id_column="po_line_id"))

        # 6. goods_receipts -> purchase_order_lines, purchase_orders
        res.append(check_foreign_key(d.get("goods_receipts", pd.DataFrame()), "goods_receipts", "po_line_id", d.get("purchase_order_lines", pd.DataFrame()), "purchase_order_lines", "po_line_id", b, child_id_column="receipt_id"))
        res.append(check_foreign_key(d.get("goods_receipts", pd.DataFrame()), "goods_receipts", "po_id", d.get("purchase_orders", pd.DataFrame()), "purchase_orders", "po_id", b, child_id_column="receipt_id"))

        # 7. operating_expenses -> branches
        res.append(check_foreign_key(d.get("operating_expenses", pd.DataFrame()), "operating_expenses", "branch_id", d.get("branches", pd.DataFrame()), "branches", "branch_id", b, child_id_column="expense_id"))

        return res

    def _compile_report(self, results: List[CheckResult], timestamp: str) -> BatchQualityReport:
        """Calculates dataset-level and batch-level metrics."""
        dataset_summaries: List[DatasetQualitySummary] = []
        dataset_failures: Dict[str, List[Dict]] = {}

        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.status == CheckStatus.PASSED.value)
        failed_checks = sum(1 for r in results if r.status == CheckStatus.FAILED.value)
        warning_checks = sum(1 for r in results if r.status == CheckStatus.WARNING.value)

        # Group by dataset
        for d in DATASETS:
            d_results = [r for r in results if r.dataset == d]
            d_rows = len(self.datasets.get(d, pd.DataFrame()))
            d_total = len(d_results)
            d_passed = sum(1 for r in d_results if r.status == CheckStatus.PASSED.value)
            d_failed = sum(1 for r in d_results if r.status == CheckStatus.FAILED.value)
            d_warn = sum(1 for r in d_results if r.status == CheckStatus.WARNING.value)

            d_score = round(
                (sum(r.quality_score for r in d_results) / d_total), 2
            ) if d_total > 0 else 100.0

            d_status = CheckStatus.PASSED.value
            if d_failed > 0:
                d_status = CheckStatus.FAILED.value
            elif d_warn > 0:
                d_status = CheckStatus.WARNING.value

            summary = DatasetQualitySummary(
                dataset=d,
                total_records=d_rows,
                total_checks=d_total,
                passed_checks=d_passed,
                failed_checks=d_failed,
                warning_checks=d_warn,
                quality_score=d_score,
                status=d_status,
            )
            dataset_summaries.append(summary)

            # Record failures
            failures = [r.to_dict() for r in d_results if r.status == CheckStatus.FAILED.value]
            if failures:
                dataset_failures[d] = failures

        # Calculate overall score across datasets
        if dataset_summaries:
            overall_score = round(
                sum(s.quality_score for s in dataset_summaries) / len(dataset_summaries), 2
            )
        else:
            overall_score = 100.0

        batch_status = CheckStatus.PASSED.value
        if failed_checks > 0:
            batch_status = CheckStatus.FAILED.value
        elif warning_checks > 0:
            batch_status = CheckStatus.WARNING.value

        return BatchQualityReport(
            batch_id=self.batch_id,
            execution_timestamp=timestamp,
            overall_quality_score=overall_score,
            total_checks_executed=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            status=batch_status,
            dataset_summaries=dataset_summaries,
            dataset_failures=dataset_failures,
            check_results=results,
        )
