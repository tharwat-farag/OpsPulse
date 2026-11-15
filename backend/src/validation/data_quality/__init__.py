"""
OpsPulse Data Quality Framework.

Provides automated, reusable data quality validation across Medallion layers:
- Completeness
- Uniqueness
- Referential Integrity
- Business Rules
- Validity
"""

from .models import (
    BatchQualityReport,
    CheckCategory,
    CheckResult,
    CheckSeverity,
    CheckStatus,
    DatasetQualitySummary,
)
from .completeness import (
    check_column_nulls,
    check_dataset_completeness,
    check_required_columns,
)
from .uniqueness import check_uniqueness
from .referential import check_foreign_key
from .validity import (
    check_accepted_values,
    check_date_validity,
    check_numeric_range,
)
from .business_rules import (
    check_custom_rule,
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
from .reporter import save_quality_reports
from .suite import QualitySuite
from .runner import main, run_data_quality_checks

__all__ = [
    "BatchQualityReport",
    "CheckCategory",
    "CheckResult",
    "CheckSeverity",
    "CheckStatus",
    "DatasetQualitySummary",
    "check_column_nulls",
    "check_dataset_completeness",
    "check_required_columns",
    "check_uniqueness",
    "check_foreign_key",
    "check_accepted_values",
    "check_date_validity",
    "check_numeric_range",
    "check_custom_rule",
    "check_goods_receipts_business_rules",
    "check_inventory_business_rules",
    "check_operating_expenses_business_rules",
    "check_product_suppliers_business_rules",
    "check_products_business_rules",
    "check_purchase_order_lines_business_rules",
    "check_purchase_orders_business_rules",
    "check_sales_business_rules",
    "check_suppliers_business_rules",
    "check_warehouses_business_rules",
    "save_quality_reports",
    "QualitySuite",
    "main",
    "run_data_quality_checks",
]
