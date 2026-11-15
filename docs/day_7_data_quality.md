# OpsPulse — Day 7: Automated Data Quality & Testing Framework

## 1. Overview and Architecture

OpsPulse is a Retail & Distribution Business Operations Intelligence platform utilizing a Medallion Architecture (Bronze, Silver, Gold) orchestrating pipelines via Apache Airflow 3.4.0 and loading an analytical PostgreSQL Data Warehouse.

In Day 7, we designed and implemented a production-grade, modular, and reusable **Data Quality & Automated Testing Framework** housed under:
`backend/src/validation/data_quality/`

The framework operates as an automated gate between the **Silver Layer** (cleaned and standardized domain entities) and the **Gold Layer** (dimensional models and facts). It ensures that data entering analytical storage is complete, unique, referentially consistent, aligned with OpsPulse business logic, and conformant with operational validity constraints.

```
                          ┌────────────────────────┐
                          │   Bronze Layer (Raw)   │
                          └───────────┬────────────┘
                                      │ Ingestion & Transformations
                                      ▼
                          ┌────────────────────────┐
                          │   Silver Layer (CSV)   │
                          └───────────┬────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
             ┌───────────────────────┐ ┌───────────────────────────┐
             │  Silver Layer Audit   │ │ Data Quality Gate (Day 7) │
             │  (Manifest & Counts)  │ │ (Completeness, Uniqueness,│
             │                       │ │  Referential, Biz Rules,  │
             │                       │ │  Validity, Reporting)     │
             └───────────┬───────────┘ └─────────────┬─────────────┘
                         └────────────┬──────────────┘
                                      │ Gate PASS
                                      ▼
                          ┌────────────────────────┐
                          │    Gold Layer (DWH)    │
                          │   (Dims, Bridges, Fact)│
                          └────────────────────────┘
```

---

## 2. Framework Architecture & Components

The framework is organized into modular single-responsibility components:

| Module | Location | Purpose |
|---|---|---|
| `models.py` | `backend/src/validation/data_quality/models.py` | Structured dataclasses (`CheckResult`, `DatasetQualitySummary`, `BatchQualityReport`) and enums (`CheckCategory`, `CheckStatus`, `CheckSeverity`). |
| `completeness.py` | `backend/src/validation/data_quality/completeness.py` | Schema existence, null counts, null percentages, critical column flagging. |
| `uniqueness.py` | `backend/src/validation/data_quality/uniqueness.py` | Single and composite primary/business key uniqueness, duplicate detection, and sample duplicate extraction. |
| `referential.py` | `backend/src/validation/data_quality/referential.py` | Cross-dataset foreign key validation, orphan record detection, orphan percentage calculation. |
| `business_rules.py` | `backend/src/validation/data_quality/business_rules.py` | Domain-specific business logic rules for sales, inventory, procurement, receipts, expenses, and partner entities. |
| `validity.py` | `backend/src/validation/data_quality/validity.py` | ISO date formatting, operational date boundaries, numeric range constraints, and accepted categorical enum sets. |
| `reporter.py` | `backend/src/validation/data_quality/reporter.py` | Generates machine-readable JSON and tabular CSV reports saved to `data/quality_reports/`. Sanitizes sensitive data. |
| `suite.py` | `backend/src/validation/data_quality/suite.py` | Declarative quality suite that configures and executes checks across all 12 Silver datasets. |
| `runner.py` | `backend/src/validation/data_quality/runner.py` | CLI and Airflow callable entry point enforcing quality gates and execution summaries. |

---

## 3. Validation Categories & Implemented Checks

### A. Completeness
- **Required Columns Check:** Verifies that all expected schema columns are present in each dataset before downstream evaluation.
- **Null Value Checks:** Measures null values per column, computing exact null record counts and null percentages.
- **Critical Columns Configuration:** Configured critical columns (e.g., `product_id`, `sales_line_id`, `net_revenue`) fail with `CRITICAL` severity, while non-critical columns can generate `WARNING` statuses.
- **Allowed Null Exceptions:** Formally excludes valid nullable operational fields (e.g., `rejection_reason` in Silver `purchase_orders`, `purchase_order_lines`, and `goods_receipts` where records are valid and unrejected).

### B. Uniqueness
- **Primary Key Uniqueness:** Validates that unique keys (`product_id`, `customer_id`, `branch_id`, `supplier_id`, `warehouse_id`, `sales_line_id`, `inventory_snapshot_id`, `po_id`, `po_line_id`, `receipt_id`, `expense_id`) have 0 duplicates.
- **Composite Key Uniqueness:** Validates composite uniqueness on bridge and snapshot tables (`product_suppliers` on `[product_id, supplier_id]`, `inventory` on `[product_id, warehouse_id, snapshot_date]`).
- **Duplicate Metrics:** Computes duplicate counts and percentages, capturing up to 10 duplicate identifiers for targeted remediation.

### C. Referential Integrity
Validates all foreign key relationships across the OpsPulse relational schema:
1. `product_suppliers.product_id` -> `products.product_id`
2. `product_suppliers.supplier_id` -> `suppliers.supplier_id`
3. `sales.product_id` -> `products.product_id`
4. `sales.customer_id` -> `customers.customer_id`
5. `sales.branch_id` -> `branches.branch_id`
6. `inventory.product_id` -> `products.product_id`
7. `inventory.warehouse_id` -> `warehouses.warehouse_id`
8. `purchase_orders.supplier_id` -> `suppliers.supplier_id`
9. `purchase_order_lines.po_id` -> `purchase_orders.po_id`
10. `purchase_order_lines.product_id` -> `products.product_id`
11. `goods_receipts.po_line_id` -> `purchase_order_lines.po_line_id`
12. `goods_receipts.po_id` -> `purchase_orders.po_id`
13. `operating_expenses.branch_id` -> `branches.branch_id`

### D. Business Rules
Implemented mathematically and operationally based on OpsPulse domain logic:
- **Sales:**
  - Positive quantities (`quantity > 0`).
  - Non-negative unit prices and unit costs (`unit_price >= 0`, `unit_cost >= 0`).
  - Non-negative discounts (`discount_amount >= 0`).
  - Gross amount calculation: `gross_amount == quantity * unit_price` (tolerance: 0.05).
  - Net revenue consistency: `net_revenue == gross_amount - discount_amount` (tolerance: 0.05).
  - Total cost calculation: `total_cost == quantity * unit_cost` (tolerance: 0.05).
  - Gross profit consistency: `gross_profit == net_revenue - total_cost` (tolerance: 0.05).
- **Inventory:**
  - Non-negative stock (`quantity_on_hand >= 0`, `quantity_reserved >= 0`).
  - Available stock calculation: `available_quantity == quantity_on_hand - quantity_reserved`.
  - Inventory valuation: `total_inventory_value == round(quantity_on_hand * standard_cost, 2)`.
  - Stockout flag consistency: `is_stockout == (quantity_on_hand == 0)`.
- **Procurement & Goods Receipts:**
  - Purchase order dates: `expected_delivery_date >= order_date`.
  - Delivery schedule calculation: `days_until_expected_delivery == (expected_delivery_date - order_date).days`.
  - Purchase order lines: `ordered_qty > 0`, `unit_cost >= 0`, `line_total == round(ordered_qty * unit_cost, 2)`.
  - Goods receipts quantity balance: `received_qty == accepted_qty + rejected_qty`.
  - Receipts dates: `received_date >= order_date`.
  - Acceptance rate: `acceptance_rate == round(accepted_qty / received_qty, 4)` (when `received_qty > 0`).
- **Operating Expenses:**
  - Expense amount must be strictly positive (`amount > 0`).
  - Date parts alignment: `expense_year == expense_date.year`, `expense_month == expense_date.month`.
- **Master Data (Products, Suppliers, Warehouses):**
  - Products: `standard_cost >= 0`, `current_selling_price >= 0`, `reorder_level >= 0`, `standard_unit_margin == current_selling_price - standard_cost`.
  - Suppliers: `0.0 <= rating <= 5.0`.
  - Warehouses: `capacity_units > 0`.
  - Product Suppliers: `supplier_price >= 0`, `lead_time_days >= 0`, `minimum_order_qty > 0`.

### E. Validity
- **Date Validity:** Evaluates parseability and year boundaries (2000–2050) for `registration_date`, `opening_date`, `sale_date`, `snapshot_date`, `order_date`, `expected_delivery_date`, `received_date`, and `expense_date`.
- **Accepted Categorical Sets:**
  - `customers.customer_type` in `['Individual', 'Business']`
  - `suppliers.rating_category` in `['Low', 'Medium', 'Good', 'Excellent']`
  - `warehouses.warehouse_capacity_category` in `['Small', 'Medium', 'Large']`
  - `sales.sales_channel` in `['In-Store', 'Online', 'Phone']`
  - `purchase_orders.status` in `['Pending', 'Partially Received', 'Fully Received', 'Cancelled']`
  - `operating_expenses.expense_quarter` in `['Q1', 'Q2', 'Q3', 'Q4']`
  - `operating_expenses.expense_category` in standard expense taxonomy (`['Rent', 'Salaries', 'Utilities', 'Marketing', 'Logistics', 'Maintenance', 'Electricity', 'Transportation', 'Insurance', 'Miscellaneous']`)
- **Numeric Ranges:** Bounds on ratings (`[0, 5]`), acceptance rates (`[0, 1]`), and costs.

---

## 4. Dataset Coverage

The framework evaluates all 12 Silver datasets in OpsPulse:

| Dataset | Row Count (Latest Batch) | Total Checks | Implemented Check Categories |
|---|---|---|---|
| `products` | 100 | 16 | Completeness, Uniqueness, Business Rules, Validity |
| `customers` | 1,000 | 10 | Completeness, Uniqueness, Business Rules, Validity |
| `branches` | 5 | 12 | Completeness, Uniqueness, Business Rules, Validity |
| `suppliers` | 10 | 13 | Completeness, Uniqueness, Business Rules, Validity |
| `warehouses` | 3 | 13 | Completeness, Uniqueness, Business Rules, Validity |
| `product_suppliers` | 150 | 13 | Completeness, Uniqueness, Referential Integrity, Business Rules |
| `sales` | 20,000 | 31 | Completeness, Uniqueness, Referential Integrity, Business Rules, Validity |
| `inventory` | 9,000 | 27 | Completeness, Uniqueness (PK & Business Key), Referential Integrity, Business Rules, Validity |
| `purchase_orders` | 1,000 | 18 | Completeness, Uniqueness, Referential Integrity, Business Rules, Validity |
| `purchase_order_lines` | 3,000 | 16 | Completeness, Uniqueness, Referential Integrity, Business Rules, Validity |
| `goods_receipts` | 1,453 | 24 | Completeness, Uniqueness, Referential Integrity, Business Rules, Validity |
| `operating_expenses` | 2,000 | 17 | Completeness, Uniqueness, Referential Integrity, Business Rules, Validity |
| **Total** | **37,721 rows** | **210 checks** | **100% Passed (Latest Real Batch)** |

---

## 5. Report Structure & Directory

Reports are written to:
`data/quality_reports/`

Each validation run generates two complementary report artifacts:
1. `quality_report_{batch_id}.json` (and `latest_quality_report.json`): Comprehensive machine-readable payload containing:
   - `batch_id`: Exact batch evaluated.
   - `execution_timestamp`: ISO 8601 UTC timestamp.
   - `overall_quality_score`: Weighted overall score across all datasets (0–100%).
   - `total_checks_executed`, `passed_checks`, `failed_checks`, `warning_checks`.
   - `status`: Overall gate status (`PASSED`, `FAILED`, or `WARNING`).
   - `dataset_summaries`: Array of dataset-level summaries with record counts, check counts, and quality scores.
   - `dataset_failures`: Detailed list of failed checks and sample failed record identifiers (omitting PII).
   - `check_results`: Complete array of all individual check executions.

2. `quality_report_{batch_id}.csv` (and `latest_quality_report.csv`): Tabular audit report containing:
   `dataset,check_name,check_category,total_records,passed_records,failed_records,quality_score,status,severity,execution_timestamp,batch_id,details,sample_failed_records`

---

## 6. Airflow Pipeline Integration

The Airflow DAG `opspulse_pipeline` was updated cleanly without breaking existing tasks or altering historical runs:

```python
    # 3. Silver audit (Manifest and record reconciliation)
    silver_audit = run_batch_module.override(
        task_id="audit_silver_layer"
    )(
        "validation.audit_silver_layer",
        batch_id,
    )

    for transform_task in transforms.values():
        transform_task >> silver_audit

    # 3b. Automated Data Quality Gate
    data_quality_gate = run_batch_module.override(
        task_id="validate_data_quality"
    )(
        "validation.data_quality.runner",
        batch_id,
    )

    silver_audit >> data_quality_gate

    # 4. Dimensions & Date Validation wait for Data Quality Gate
    for dimension_task in dimensions.values():
        data_quality_gate >> dimension_task

    data_quality_gate >> date_check
```

### Quality Gate Enforcement:
- If critical checks fail, `validation.data_quality.runner.main` raises `RuntimeError`, immediately failing the `validate_data_quality` Airflow task and halting all downstream Dimension and Fact warehouse loading.
- If non-critical warnings are detected, they are flagged in the report while allowing the pipeline to proceed.
- Downstream Gold warehouse loading and reconciliation logic remain 100% intact and untouched.

---

## 7. Automated Testing Results

Automated unit and integration tests were implemented under `tests/` using `pytest`:

```bash
pytest -v
```

### Test Suite Execution Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.2.0, pluggy-1.7.0 -- .venv\Scripts\python.exe
rootdir: D:\Data Engineer Projects\OpsPulse
configfile: pytest.ini
testpaths: tests
collected 36 items

tests/test_business_rules.py::test_sales_business_rules_valid PASSED     [  2%]
tests/test_business_rules.py::test_sales_business_rules_violations PASSED [  5%]
tests/test_business_rules.py::test_inventory_business_rules_valid PASSED [  8%]
tests/test_business_rules.py::test_inventory_business_rules_violations PASSED [ 11%]
tests/test_business_rules.py::test_purchase_orders_business_rules PASSED [ 13%]
tests/test_business_rules.py::test_goods_receipts_quantity_balance PASSED [ 16%]
tests/test_business_rules.py::test_operating_expenses_business_rules PASSED [ 19%]
tests/test_completeness.py::test_required_columns_success PASSED         [ 22%]
tests/test_completeness.py::test_required_columns_missing PASSED         [ 25%]
tests/test_completeness.py::test_column_nulls_no_nulls PASSED            [ 27%]
tests/test_completeness.py::test_column_nulls_with_nulls_critical PASSED [ 30%]
tests/test_completeness.py::test_column_nulls_with_nulls_non_critical PASSED [ 33%]
tests/test_completeness.py::test_empty_dataframe_completeness PASSED     [ 36%]
tests/test_referential.py::test_foreign_key_valid_references PASSED      [ 38%]
tests/test_referential.py::test_foreign_key_orphan_detection PASSED      [ 41%]
tests/test_referential.py::test_foreign_key_empty_child PASSED           [ 44%]
tests/test_referential.py::test_foreign_key_empty_parent PASSED          [ 47%]
tests/test_referential.py::test_foreign_key_missing_columns PASSED       [ 50%]
tests/test_reporter.py::test_report_generation PASSED                    [ 52%]
tests/test_suite_and_runner.py::test_suite_valid_synthetic_data PASSED   [ 55%]
tests/test_suite_and_runner.py::test_suite_detects_violations PASSED     [ 58%]
tests/test_suite_and_runner.py::test_suite_handles_empty_datasets PASSED [ 61%]
tests/test_suite_and_runner.py::test_runner_halts_on_failure PASSED      [ 63%]
tests/test_suite_and_runner.py::test_runner_no_halt_option PASSED        [ 66%]
tests/test_uniqueness.py::test_single_pk_uniqueness_success PASSED       [ 69%]
tests/test_uniqueness.py::test_single_pk_uniqueness_duplicates_found PASSED [ 72%]
tests/test_composite_key_uniqueness_success PASSED   [ 75%]
tests/test_composite_key_uniqueness_duplicates_found PASSED [ 77%]
tests/test_uniqueness.py::test_uniqueness_empty_dataframe PASSED         [ 80%]
tests/test_uniqueness.py::test_uniqueness_missing_column PASSED          [ 83%]
tests/test_validity.py::test_date_validity_success PASSED                [ 86%]
tests/test_validity.py::test_date_validity_invalid_formats PASSED        [ 88%]
tests/test_accepted_values_success PASSED              [ 91%]
tests/test_accepted_values_violations PASSED           [ 94%]
tests/test_numeric_range_success PASSED                [ 97%]
tests/test_numeric_range_violations PASSED             [100%]

============================= 36 passed in 0.76s ==============================
```

All 36 unit and integration test cases passed across all test categories using isolated synthetic datasets.

---

## 8. Verification on Production Silver Batch

The framework was verified directly against the latest Silver production batch:
`batch_20261115_051056_1d64c5da`

### Execution Output:
```
================================================================================
OPSPULSE - AUTOMATED DATA QUALITY GATE
Batch ID: batch_20261115_051056_1d64c5da
================================================================================

Dataset Quality Summary:
             Dataset Records  Checks  Passed  Failed  Score Status
            products     100      16      16       0 100.0% PASSED
           customers   1,000      10      10       0 100.0% PASSED
            branches       5      12      12       0 100.0% PASSED
           suppliers      10      13      13       0 100.0% PASSED
          warehouses       3      13      13       0 100.0% PASSED
   product_suppliers     150      13      13       0 100.0% PASSED
               sales  20,000      31      31       0 100.0% PASSED
           inventory   9,000      27      27       0 100.0% PASSED
     purchase_orders   1,000      18      18       0 100.0% PASSED
purchase_order_lines   3,000      16      16       0 100.0% PASSED
      goods_receipts   1,453      24      24       0 100.0% PASSED
  operating_expenses   2,000      17      17       0 100.0% PASSED

--------------------------------------------------------------------------------
Overall Quality Score: 100.00%
Total Checks Executed: 210
Passed Checks:         210
Failed Checks:         0
Warning Checks:        0
Batch Status:          PASSED
Reports Generated:
  JSON: D:\Data Engineer Projects\OpsPulse\data\quality_reports\quality_report_batch_20261115_051056_1d64c5da.json
  CSV:  D:\Data Engineer Projects\OpsPulse\data\quality_reports\quality_report_batch_20261115_051056_1d64c5da.csv
--------------------------------------------------------------------------------

DATA QUALITY GATE PASSED.
```

---

## 9. How to Run the Framework

### 1. Run Automated Unit & Integration Tests:
```bash
pytest -v
```

### 2. Run Data Quality Checks on a Silver Batch via CLI:
```bash
# Windows
python backend/src/validation/data_quality/runner.py batch_20261115_051056_1d64c5da

# Linux / WSL
python backend/src/validation/data_quality/runner.py batch_20261115_051056_1d64c5da
```

### 3. Optional Non-Halting Mode (Run without raising exceptions on failure):
```bash
python backend/src/validation/data_quality/runner.py batch_20261115_051056_1d64c5da --no-halt
```

### 4. Run Existing Silver Layer Manifest Audit:
```bash
python backend/src/validation/audit_silver_layer.py batch_20261115_051056_1d64c5da
```

---

## 10. Known Limitations & Future Considerations

1. **In-Memory Batch Processing:** The current framework processes batches using pandas DataFrames. For the current data scale (thousands to tens of thousands of records per batch), execution is sub-second. If individual batch volumes exceed millions of rows, chunked processing or PySpark DataFrames can be plugged into the modular check interfaces.
2. **Dynamic Cross-Batch Historical Drift:** The current framework validates within the current ingestion batch and against current Silver dimensional state. Statistical distribution drift detection (e.g. KS tests on sales amounts over 30 days) is planned for future monitoring extensions.
3. **Database Schema Intactness:** No schema alterations were made to the PostgreSQL data warehouse or existing Gold tables. All quality gates operate before database ingestion.
