"""
Tests for Data Quality Completeness module.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

# Ensure backend/src is in sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.completeness import (
    check_column_nulls,
    check_dataset_completeness,
    check_required_columns,
)
from validation.data_quality.models import CheckCategory, CheckSeverity, CheckStatus


def test_required_columns_success():
    df = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
    result = check_required_columns(
        df=df,
        dataset="test_data",
        required_columns=["col_a", "col_b"],
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0
    assert result.check_category == CheckCategory.COMPLETENESS.value


def test_required_columns_missing():
    df = pd.DataFrame({"col_a": [1, 2]})
    result = check_required_columns(
        df=df,
        dataset="test_data",
        required_columns=["col_a", "col_b", "col_c"],
        batch_id="test_batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records > 0
    assert result.quality_score == 0.0
    assert "col_b" in result.details
    assert "col_c" in result.details


def test_column_nulls_no_nulls():
    df = pd.DataFrame({"id": ["1", "2"], "amount": [10.5, 20.0]})
    result = check_column_nulls(
        df=df,
        dataset="test_data",
        column="amount",
        batch_id="test_batch_001",
        critical_columns={"amount"},
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0


def test_column_nulls_with_nulls_critical():
    df = pd.DataFrame({"id": ["1", "2", "3", "4"], "amount": [10.0, None, 30.0, None]})
    result = check_column_nulls(
        df=df,
        dataset="test_data",
        column="amount",
        batch_id="test_batch_001",
        critical_columns={"amount"},
        id_column="id",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 2
    assert result.total_records == 4
    assert result.quality_score == 50.0
    assert result.severity == CheckSeverity.CRITICAL.value
    assert "2 nulls (50.0%)" in result.details
    assert "2" in result.sample_failed_records


def test_column_nulls_with_nulls_non_critical():
    df = pd.DataFrame({"id": ["1", "2"], "notes": ["hello", None]})
    result = check_column_nulls(
        df=df,
        dataset="test_data",
        column="notes",
        batch_id="test_batch_001",
        critical_columns={"id"},
        id_column="id",
    )
    assert result.status == CheckStatus.WARNING.value
    assert result.failed_records == 1
    assert result.severity == CheckSeverity.WARNING.value


def test_empty_dataframe_completeness():
    df = pd.DataFrame(columns=["id", "name"])
    results = check_dataset_completeness(
        df=df,
        dataset="test_data",
        required_columns=["id", "name"],
        critical_columns=["id"],
        batch_id="test_batch_001",
    )
    # Required columns exist, even if 0 rows
    assert results[0].status == CheckStatus.PASSED.value
    # Null checks on 0 rows return passed with 0 total records
    for res in results[1:]:
        assert res.status == CheckStatus.PASSED.value
        assert res.total_records == 0
