"""
OpsPulse Data Quality Framework - Validity Checks.

Implements reusable domain validity validations:
- Date parsing and ISO formatting
- Date range and chronological bounds
- Numeric range constraints (min, max)
- Accepted categorical values (enum sets)
- Invalid format and type detection
"""

from typing import Any, Iterable, List, Optional, Set
import pandas as pd

from .models import CheckCategory, CheckResult, CheckSeverity


def check_date_validity(
    df: pd.DataFrame,
    dataset: str,
    date_column: str,
    batch_id: str,
    id_column: Optional[str] = None,
    min_year: int = 2000,
    max_year: int = 2050,
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that a date column contains valid, parseable dates formatted as YYYY-MM-DD
    and fall within an acceptable historical and operational year range.
    """
    total_records = len(df)
    check_name = f"{dataset}_{date_column}_valid_date"

    if date_column not in df.columns:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Column '{date_column}' missing in dataset '{dataset}'.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no dates to validate in '{date_column}'.",
        )

    # Attempt date parsing
    parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
    invalid_mask = parsed_dates.isna() & df[date_column].notna()

    # Out of bounds check
    year_mask = (parsed_dates.dt.year < min_year) | (parsed_dates.dt.year > max_year)
    total_invalid_mask = invalid_mask | year_mask.fillna(False)

    failed_count = int(total_invalid_mask.sum())
    sample_failures: List[Any] = []

    if failed_count > 0:
        if id_column and id_column in df.columns:
            sample_failures = (
                df.loc[total_invalid_mask, id_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_failures = (
                df.loc[total_invalid_mask, date_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )

        fail_pct = round((failed_count / total_records) * 100.0, 2)
        details = (
            f"Found {failed_count} invalid date records ({fail_pct}%) in '{date_column}'. "
            f"Expected parseable date between {min_year} and {max_year}."
        )
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=total_records,
            failed_records=failed_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_failures,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=check_name,
        category=CheckCategory.VALIDITY,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"All {total_records:,} records contain valid dates in '{date_column}' ({min_year}-{max_year}).",
    )


def check_accepted_values(
    df: pd.DataFrame,
    dataset: str,
    column: str,
    accepted_values: Iterable[Any],
    batch_id: str,
    id_column: Optional[str] = None,
    allow_nulls: bool = False,
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that categorical column values belong to a predefined set of accepted values.
    """
    total_records = len(df)
    check_name = f"{dataset}_{column}_accepted_values"
    allowed_set = set(accepted_values)
    allowed_display = ", ".join(sorted(str(v) for v in allowed_set))

    if column not in df.columns:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Column '{column}' missing in dataset '{dataset}'.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no values to check for '{column}'.",
        )

    if allow_nulls:
        invalid_mask = df[column].notna() & (~df[column].isin(allowed_set))
    else:
        invalid_mask = ~df[column].isin(allowed_set)

    failed_count = int(invalid_mask.sum())
    sample_failures: List[Any] = []

    if failed_count > 0:
        if id_column and id_column in df.columns:
            sample_failures = (
                df.loc[invalid_mask, id_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_failures = (
                df.loc[invalid_mask, column]
                .dropna()
                .astype(str)
                .unique()[:10]
                .tolist()
            )

        fail_pct = round((failed_count / total_records) * 100.0, 2)
        details = (
            f"Found {failed_count} records ({fail_pct}%) with unexpected values in '{column}'. "
            f"Allowed: [{allowed_display}]."
        )
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=total_records,
            failed_records=failed_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_failures,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=check_name,
        category=CheckCategory.VALIDITY,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"All {total_records:,} records in '{column}' conform to allowed values: [{allowed_display}].",
    )


def check_numeric_range(
    df: pd.DataFrame,
    dataset: str,
    column: str,
    batch_id: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    id_column: Optional[str] = None,
    allow_nulls: bool = False,
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that a numeric column falls within [min_value, max_value].
    """
    total_records = len(df)
    check_name = f"{dataset}_{column}_numeric_range"

    bounds_desc = []
    if min_value is not None:
        bounds_desc.append(f">= {min_value}")
    if max_value is not None:
        bounds_desc.append(f"<= {max_value}")
    range_str = " and ".join(bounds_desc) if bounds_desc else "any number"

    if column not in df.columns:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Column '{column}' missing in dataset '{dataset}'.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Dataset is empty; no values to check for '{column}'.",
        )

    numeric_series = pd.to_numeric(df[column], errors="coerce")
    unparseable_mask = numeric_series.isna() & df[column].notna()

    out_of_bounds_mask = pd.Series(False, index=df.index)
    if min_value is not None:
        out_of_bounds_mask |= numeric_series < min_value
    if max_value is not None:
        out_of_bounds_mask |= numeric_series > max_value

    if not allow_nulls:
        total_invalid_mask = unparseable_mask | out_of_bounds_mask | df[column].isna()
    else:
        total_invalid_mask = unparseable_mask | (df[column].notna() & out_of_bounds_mask)

    failed_count = int(total_invalid_mask.sum())
    sample_failures: List[Any] = []

    if failed_count > 0:
        if id_column and id_column in df.columns:
            sample_failures = (
                df.loc[total_invalid_mask, id_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_failures = (
                df.loc[total_invalid_mask, column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )

        fail_pct = round((failed_count / total_records) * 100.0, 2)
        details = (
            f"Found {failed_count} records ({fail_pct}%) outside expected range in '{column}'. "
            f"Expected: {range_str}."
        )
        return CheckResult.create(
            dataset=dataset,
            check_name=check_name,
            category=CheckCategory.VALIDITY,
            total_records=total_records,
            failed_records=failed_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_failures,
        )

    return CheckResult.create(
        dataset=dataset,
        check_name=check_name,
        category=CheckCategory.VALIDITY,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=f"All {total_records:,} records in '{column}' fall within range: {range_str}.",
    )
