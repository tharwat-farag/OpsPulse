"""
Tests for Data Quality Uniqueness module.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.models import CheckCategory, CheckStatus
from validation.data_quality.uniqueness import check_uniqueness


def test_single_pk_uniqueness_success():
    df = pd.DataFrame({"product_id": ["P001", "P002", "P003"], "price": [10, 20, 30]})
    result = check_uniqueness(
        df=df,
        dataset="products",
        key_columns="product_id",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0
    assert result.check_category == CheckCategory.UNIQUENESS.value


def test_single_pk_uniqueness_duplicates_found():
    df = pd.DataFrame({
        "product_id": ["P001", "P002", "P001", "P003", "P001"],
        "price": [10, 20, 10, 30, 15],
    })
    result = check_uniqueness(
        df=df,
        dataset="products",
        key_columns="product_id",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 2  # 2 duplicates of P001
    assert result.total_records == 5
    assert result.quality_score == 60.0
    assert "2 duplicate records (40.0%)" in result.details
    assert "P001" in result.sample_failed_records


def test_composite_key_uniqueness_success():
    df = pd.DataFrame({
        "product_id": ["P001", "P001", "P002"],
        "supplier_id": ["S001", "S002", "S001"],
    })
    result = check_uniqueness(
        df=df,
        dataset="product_suppliers",
        key_columns=["product_id", "supplier_id"],
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0


def test_composite_key_uniqueness_duplicates_found():
    df = pd.DataFrame({
        "product_id": ["P001", "P001", "P002", "P001"],
        "supplier_id": ["S001", "S001", "S001", "S002"],
    })
    result = check_uniqueness(
        df=df,
        dataset="product_suppliers",
        key_columns=["product_id", "supplier_id"],
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 1
    assert result.quality_score == 75.0
    assert len(result.sample_failed_records) == 1
    assert result.sample_failed_records[0]["product_id"] == "P001"
    assert result.sample_failed_records[0]["supplier_id"] == "S001"


def test_uniqueness_empty_dataframe():
    df = pd.DataFrame(columns=["id", "val"])
    result = check_uniqueness(
        df=df,
        dataset="empty_data",
        key_columns="id",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.total_records == 0
    assert result.failed_records == 0


def test_uniqueness_missing_column():
    df = pd.DataFrame({"other_col": [1, 2]})
    result = check_uniqueness(
        df=df,
        dataset="bad_data",
        key_columns="missing_pk",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert "missing key columns" in result.details
