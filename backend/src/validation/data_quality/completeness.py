"""
OpsPulse Data Quality Framework - Completeness Checks.

Implements reusable completeness validations:
- Required column presence
- Column-level null value detection
- Null percentage calculation
- Configurable critical column handling
"""

from typing import Any, Dict, List, Optional, Set
import pandas as pd

from .models import CheckCategory, CheckResult, CheckSeverity


def check_required_columns(
    df: pd.DataFrame,
    dataset: str,
    required_columns: List[str],
    batch_id: str,
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that all expected columns exist in the dataset.
    """
    total_records = len(df)
    existing_cols = set(df.columns)
    missing_cols = [col for col in required_columns if col not in existing_cols]

    if missing_cols:
        details = f"Missing required columns: {missing_cols}"
        failed_records = total_records if total_records > 0 else 1
        return CheckResult.create(
            dataset=dataset,
            check_name=f"{dataset}_required_columns_exist",
            category=CheckCategory.COMPLETENESS,
            total_records=max(total_records, 1),
            failed_records=failed_records,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=missing_cols,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=f"{dataset}_required_columns_exist",
        category=CheckCategory.COMPLETENESS,
        total_records=max(total_records, 1),
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"All {len(required_columns)} required columns present.",
    )


def check_column_nulls(
    df: pd.DataFrame,
    dataset: str,
    column: str,
    batch_id: str,
    critical_columns: Optional[Set[str]] = None,
    id_column: Optional[str] = None,
    max_null_pct_threshold: float = 0.0,
) -> CheckResult:
    """
    Checks for NULL/NA values in a specific column, calculating null count and percentage.
    If the column is in critical_columns, severity is CRITICAL; otherwise WARNING.
    """
    total_records = len(df)
    is_critical = critical_columns is not None and column in critical_columns
    severity = CheckSeverity.CRITICAL if is_critical else CheckSeverity.WARNING

    if column not in df.columns:
        return CheckResult.create(
            dataset=dataset,
            check_name=f"{dataset}_{column}_null_check",
            category=CheckCategory.COMPLETENESS,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Column '{column}' does not exist in dataset.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=f"{dataset}_{column}_null_check",
            category=CheckCategory.COMPLETENESS,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no rows to check for nulls in '{column}'.",
        )

    null_mask = df[column].isna()
    null_count = int(null_mask.sum())
    null_pct = round((null_count / total_records) * 100.0, 2)

    sample_identifiers = []
    if null_count > 0:
        if id_column and id_column in df.columns:
            sample_identifiers = df.loc[null_mask, id_column].dropna().head(10).tolist()
        else:
            sample_identifiers = df[null_mask].index[:10].tolist()

    details = f"Column '{column}': {null_count} nulls ({null_pct}%)."
    
    # Check if null percentage exceeds allowed threshold
    if null_pct > max_null_pct_threshold:
        return CheckResult.create(
            dataset=dataset,
            check_name=f"{dataset}_{column}_null_check",
            category=CheckCategory.COMPLETENESS,
            total_records=total_records,
            failed_records=null_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_identifiers,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=f"{dataset}_{column}_null_check",
        category=CheckCategory.COMPLETENESS,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"Column '{column}' passed null check ({null_pct}% nulls, threshold: {max_null_pct_threshold}%).",
    )


def check_dataset_completeness(
    df: pd.DataFrame,
    dataset: str,
    required_columns: List[str],
    critical_columns: Optional[List[str]],
    batch_id: str,
    id_column: Optional[str] = None,
    allow_null_columns: Optional[Set[str]] = None,
) -> List[CheckResult]:
    """
    Runs a full completeness suite on the dataset:
    1. Schema existence check for all required columns.
    2. Column-by-column null checks for required columns (excluding optionally allowed nullable columns).
    """
    results: List[CheckResult] = []
    
    # 1. Required columns presence
    results.append(
        check_required_columns(
            df=df,
            dataset=dataset,
            required_columns=required_columns,
            batch_id=batch_id,
            severity=CheckSeverity.CRITICAL,
        )
    )

    # If any required column is missing, still run null checks on existing ones
    crit_set = set(critical_columns or [])
    allowed_nulls = allow_null_columns or set()

    for col in required_columns:
        if col in df.columns and col not in allowed_nulls:
            results.append(
                check_column_nulls(
                    df=df,
                    dataset=dataset,
                    column=col,
                    batch_id=batch_id,
                    critical_columns=crit_set,
                    id_column=id_column,
                )
            )

    return results
