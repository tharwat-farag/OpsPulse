"""
OpsPulse Data Quality Framework - Uniqueness Checks.

Implements reusable uniqueness validations:
- Primary and business key uniqueness
- Composite key uniqueness
- Duplicate count and duplicate percentage calculation
- Sample duplicate identifier collection
"""

from typing import Any, List, Optional, Union
import pandas as pd

from .models import CheckCategory, CheckResult, CheckSeverity


def check_uniqueness(
    df: pd.DataFrame,
    dataset: str,
    key_columns: Union[str, List[str]],
    batch_id: str,
    check_name_suffix: str = "primary_key",
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that the specified key columns (single or composite) contain no duplicate values.
    Calculates duplicate count and duplicate percentage.
    """
    total_records = len(df)
    cols = [key_columns] if isinstance(key_columns, str) else list(key_columns)
    cols_display = ", ".join(cols)
    check_name = f"{dataset}_{check_name_suffix}_uniqueness"

    # Verify columns exist
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.UNIQUENESS,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Cannot evaluate uniqueness: missing key columns {missing_cols}.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.UNIQUENESS,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no records to evaluate for key [{cols_display}].",
        )

    # Detect duplicates
    duplicate_mask = df.duplicated(subset=cols, keep="first")
    duplicate_count = int(duplicate_mask.sum())
    duplicate_pct = round((duplicate_count / total_records) * 100.0, 2)

    sample_duplicates: List[Any] = []
    if duplicate_count > 0:
        # Extract duplicate keys
        if len(cols) == 1:
            sample_duplicates = (
                df.loc[duplicate_mask, cols[0]]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_duplicates = [
                dict(row)
                for row in df.loc[duplicate_mask, cols].head(10).to_dict(orient="records")
            ]

        details = (
            f"Found {duplicate_count} duplicate records ({duplicate_pct}%) "
            f"on key [{cols_display}]."
        )
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.UNIQUENESS,
            total_records=total_records,
            failed_records=duplicate_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_duplicates,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=check_name,
        category=CheckCategory.UNIQUENESS,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"Key [{cols_display}] is completely unique across all {total_records:,} records.",
    )
