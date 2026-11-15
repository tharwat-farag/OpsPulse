"""
Tests for Data Quality Validity module.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.data_quality.models import CheckCategory, CheckStatus
from validation.data_quality.validity import (
    check_accepted_values,
    check_date_validity,
    check_numeric_range,
)


def test_date_validity_success():
    df = pd.DataFrame({"sale_date": ["2025-01-01", "2025-05-15", "2024-12-31"]})
    result = check_date_validity(
        df=df,
        dataset="sales",
        date_column="sale_date",
        batch_id="batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0
    assert result.quality_score == 100.0


def test_date_validity_invalid_formats():
    df = pd.DataFrame({"sale_date": ["2025-01-01", "not-a-date", "1990-01-01", "3000-01-01"]})
    result = check_date_validity(
        df=df,
        dataset="sales",
        date_column="sale_date",
        batch_id="batch_001",
        min_year=2000,
        max_year=2050,
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 3  # not-a-date, 1990 (<2000), 3000 (>2050)
    assert result.quality_score == 25.0


def test_accepted_values_success():
    df = pd.DataFrame({"channel": ["In-Store", "Online", "In-Store"]})
    result = check_accepted_values(
        df=df,
        dataset="sales",
        column="channel",
        accepted_values=["In-Store", "Online", "Phone"],
        batch_id="batch_001",
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0


def test_accepted_values_violations():
    df = pd.DataFrame({"channel": ["In-Store", "DroneDelivery", "Online"]})
    result = check_accepted_values(
        df=df,
        dataset="sales",
        column="channel",
        accepted_values=["In-Store", "Online", "Phone"],
        batch_id="batch_001",
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 1
    assert "DroneDelivery" in result.sample_failed_records


def test_numeric_range_success():
    df = pd.DataFrame({"rating": [3.5, 4.0, 5.0, 0.0]})
    result = check_numeric_range(
        df=df,
        dataset="suppliers",
        column="rating",
        batch_id="batch_001",
        min_value=0.0,
        max_value=5.0,
    )
    assert result.status == CheckStatus.PASSED.value
    assert result.failed_records == 0


def test_numeric_range_violations():
    df = pd.DataFrame({"rating": [3.5, -1.0, 6.2]})
    result = check_numeric_range(
        df=df,
        dataset="suppliers",
        column="rating",
        batch_id="batch_001",
        min_value=0.0,
        max_value=5.0,
    )
    assert result.status == CheckStatus.FAILED.value
    assert result.failed_records == 2
    assert result.quality_score == round(1 / 3 * 100, 2)
