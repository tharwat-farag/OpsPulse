"""
Tests for Data Quality Suite and Runner modules.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.models import CheckStatus
from validation.data_quality.runner import run_data_quality_checks
from validation.data_quality.suite import QualitySuite


def test_suite_valid_synthetic_data(valid_synthetic_datasets):
    suite = QualitySuite(batch_id="batch_valid_test", datasets_data=valid_synthetic_datasets)
    report = suite.run()

    assert report.batch_id == "batch_valid_test"
    assert report.status == CheckStatus.PASSED.value
    assert report.failed_checks == 0
    assert report.overall_quality_score == 100.0
    assert len(report.dataset_summaries) == 12
    # Verify every check result carries the batch_id
    for r in report.check_results:
        assert r.batch_id == "batch_valid_test"


def test_suite_detects_violations(valid_synthetic_datasets):
    data = dict(valid_synthetic_datasets)
    # Inject a violation in sales (negative quantity)
    bad_sales = data["sales"].copy()
    bad_sales.loc[0, "quantity"] = -10
    data["sales"] = bad_sales

    suite = QualitySuite(batch_id="batch_invalid_test", datasets_data=data)
    report = suite.run()

    assert report.status == CheckStatus.FAILED.value
    assert report.failed_checks > 0
    assert "sales" in report.dataset_failures


def test_suite_handles_empty_datasets():
    empty_datasets = {
        name: pd.DataFrame()
        for name in [
            "products", "customers", "branches", "suppliers", "warehouses",
            "product_suppliers", "sales", "inventory", "purchase_orders",
            "purchase_order_lines", "goods_receipts", "operating_expenses"
        ]
    }
    suite = QualitySuite(batch_id="batch_empty_test", datasets_data=empty_datasets)
    report = suite.run()
    assert report.batch_id == "batch_empty_test"
    assert len(report.dataset_summaries) == 12


def test_runner_halts_on_failure(tmp_path: Path):
    silver_dir = tmp_path / "silver"
    batch_dir = silver_dir / "batch_failing_test"
    batch_dir.mkdir(parents=True)

    # Write broken products csv missing required columns
    bad_products = pd.DataFrame({"some_random_col": [1, 2, 3]})
    bad_products.to_csv(batch_dir / "products.csv", index=False)

    reports_dir = tmp_path / "reports"

    with pytest.raises(RuntimeError, match="Data Quality Gate FAILED"):
        run_data_quality_checks(
            batch_id="batch_failing_test",
            silver_dir=silver_dir,
            output_reports_dir=reports_dir,
            halt_on_critical_failure=True,
        )


def test_runner_no_halt_option(tmp_path: Path):
    silver_dir = tmp_path / "silver"
    batch_dir = silver_dir / "batch_warning_test"
    batch_dir.mkdir(parents=True)

    bad_products = pd.DataFrame({"some_random_col": [1, 2, 3]})
    bad_products.to_csv(batch_dir / "products.csv", index=False)

    reports_dir = tmp_path / "reports"

    # With halt_on_critical_failure=False, returns report instead of raising
    report = run_data_quality_checks(
        batch_id="batch_warning_test",
        silver_dir=silver_dir,
        output_reports_dir=reports_dir,
        halt_on_critical_failure=False,
    )
    assert report.status == CheckStatus.FAILED.value
    assert report.failed_checks > 0
