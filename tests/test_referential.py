"""
Tests for Data Quality Referential Integrity module.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.models import CheckCategory, CheckStatus
from validation.data_quality.referential import check_foreign_key


def test_foreign_key_valid_references():
    parent_df = pd.DataFrame({"product_id": ["P001", "P002", "P003"]})
    child_df = pd.DataFrame({"sales_id": ["S1", "S2", "S3"], "product_id": ["P001", "P002", "P001"]})

    result = check_foreign_key(
        child_df=child_df,
        child_dataset="sales",
        child_column="product_id",
        parent_df=parent_df,
        parent_dataset="products",
        parent_column="product_id",
        batch_id="test_batch_001",
        child_id_column="sales_id",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0
    assert result.check_category == CheckCategory.REFERENTIAL_INTEGRITY.value


def test_foreign_key_orphan_detection():
    parent_df = pd.DataFrame({"product_id": ["P001", "P002"]})
    child_df = pd.DataFrame({
        "sales_id": ["S1", "S2", "S3", "S4"],
        "product_id": ["P001", "P999", "P002", "P888"],
    })

    result = check_foreign_key(
        child_df=child_df,
        child_dataset="sales",
        child_column="product_id",
        parent_df=parent_df,
        parent_dataset="products",
        parent_column="product_id",
        batch_id="test_batch_001",
        child_id_column="sales_id",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 2
    assert result.total_records == 4
    assert result.quality_score == 50.0
    assert "Found 2 orphan records (50.0%)" in result.details
    assert "S2" in result.sample_failed_records
    assert "S4" in result.sample_failed_records


def test_foreign_key_empty_child():
    parent_df = pd.DataFrame({"product_id": ["P001"]})
    child_df = pd.DataFrame(columns=["sales_id", "product_id"])

    result = check_foreign_key(
        child_df=child_df,
        child_dataset="sales",
        child_column="product_id",
        parent_df=parent_df,
        parent_dataset="products",
        parent_column="product_id",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.total_records == 0
    assert result.failed_records == 0


def test_foreign_key_empty_parent():
    parent_df = pd.DataFrame(columns=["product_id"])
    child_df = pd.DataFrame({"sales_id": ["S1"], "product_id": ["P001"]})

    result = check_foreign_key(
        child_df=child_df,
        child_dataset="sales",
        child_column="product_id",
        parent_df=parent_df,
        parent_dataset="products",
        parent_column="product_id",
        batch_id="test_batch_001",
    )
    # Child has 1 row with no matching parent -> 1 orphan
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 1
    assert result.quality_score == 0.0


def test_foreign_key_missing_columns():
    parent_df = pd.DataFrame({"product_id": ["P001"]})
    child_df = pd.DataFrame({"sales_id": ["S1"]})

    result = check_foreign_key(
        child_df=child_df,
        child_dataset="sales",
        child_column="product_id",  # missing in child
        parent_df=parent_df,
        parent_dataset="products",
        parent_column="product_id",
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert "Child column 'product_id' missing" in result.details
