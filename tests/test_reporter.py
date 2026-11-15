"""
Tests for Data Quality Reporter module.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.models import (
    BatchQualityReport,
    CheckCategory,
    CheckResult,
    DatasetQualitySummary,
)
from validation.data_quality.reporter import save_quality_reports


def test_report_generation(tmp_path: Path):
    res1 = CheckResult.create(
        dataset="products",
        check_name="products_pk_unique",
        category=CheckCategory.UNIQUENESS,
        total_records=10,
        failed_records=0,
        batch_id="test_batch_123",
    )
    res2 = CheckResult.create(
        dataset="sales",
        check_name="sales_qty_positive",
        category=CheckCategory.BUSINESS_RULES,
        total_records=10,
        failed_records=1,
        batch_id="test_batch_123",
        sample_failed_records=["SL_BAD_01"],
    )

    summary_products = DatasetQualitySummary(
        dataset="products",
        total_records=10,
        total_checks=1,
        passed_checks=1,
        failed_checks=0,
        warning_checks=0,
        quality_score=100.0,
        status="PASSED",
    )
    summary_sales = DatasetQualitySummary(
        dataset="sales",
        total_records=10,
        total_checks=1,
        passed_checks=0,
        failed_checks=1,
        warning_checks=0,
        quality_score=90.0,
        status="FAILED",
    )

    report = BatchQualityReport(
        batch_id="test_batch_123",
        execution_timestamp="2026-11-15T12:00:00Z",
        overall_quality_score=95.0,
        total_checks_executed=2,
        passed_checks=1,
        failed_checks=1,
        warning_checks=0,
        status="FAILED",
        dataset_summaries=[summary_products, summary_sales],
        dataset_failures={"sales": [res2.to_dict()]},
        check_results=[res1, res2],
    )

    json_path, csv_path = save_quality_reports(report, output_dir=tmp_path)

    # Verify JSON
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert loaded_json["batch_id"] == "test_batch_123"
    assert loaded_json["overall_quality_score"] == 95.0
    assert loaded_json["total_checks_executed"] == 2
    assert len(loaded_json["dataset_summaries"]) == 2
    assert "sales" in loaded_json["dataset_failures"]

    # Verify CSV
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == 2
    assert set(df["dataset"].unique()) == {"products", "sales"}
    assert "SL_BAD_01" in str(df.loc[df["dataset"] == "sales", "sample_failed_records"].values[0])
