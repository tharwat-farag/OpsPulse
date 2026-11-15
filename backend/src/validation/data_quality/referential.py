"""
OpsPulse Data Quality Framework - Referential Integrity Checks.

Implements cross-dataset relationship validations:
- Foreign key reference integrity
- Orphan record detection
- Orphan record percentage calculation
- Sample orphan identifier collection
"""

from typing import Any, List, Optional
import pandas as pd

from .models import CheckCategory, CheckResult, CheckSeverity


def check_foreign_key(
    child_df: pd.DataFrame,
    child_dataset: str,
    child_column: str,
    parent_df: pd.DataFrame,
    parent_dataset: str,
    parent_column: str,
    batch_id: str,
    child_id_column: Optional[str] = None,
    allow_nulls: bool = False,
    severity: CheckSeverity = CheckSeverity.CRITICAL,
) -> CheckResult:
    """
    Validates that foreign key values in child_df[child_column] exist in parent_df[parent_column].
    Detects orphan records and computes orphan counts and percentages.
    """
    total_records = len(child_df)
    check_name = f"{child_dataset}_{child_column}_fkey_{parent_dataset}_{parent_column}"

    # Verify column existence
    if child_column not in child_df.columns:
        return CheckResult.create(
            dataset=child_dataset,
            check_name=check_name,
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Child column '{child_column}' missing in dataset '{child_dataset}'.",
        )

    if parent_column not in parent_df.columns:
        return CheckResult.create(
            dataset=child_dataset,
            check_name=check_name,
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            total_records=max(total_records, 1),
            failed_records=max(total_records, 1),
            batch_id=batch_id,
            severity=severity,
            details=f"Parent column '{parent_column}' missing in parent dataset '{parent_dataset}'.",
        )

    if total_records == 0:
        return CheckResult.create(
            dataset=child_dataset,
            check_name=check_name,
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            total_records=0,
            failed_records=0,
            batch_id=batch_id,
            severity=severity,
            details=f"Child dataset '{child_dataset}' is empty; no foreign keys to check.",
        )

    # Extract valid parent keys set
    valid_keys = set(parent_df[parent_column].dropna().unique())

    # Build mask for orphan records
    if allow_nulls:
        # Null values are permitted and not considered orphans
        eval_mask = child_df[child_column].notna()
        evaluated_count = int(eval_mask.sum())
        orphan_mask = eval_mask & (~child_df[child_column].isin(valid_keys))
    else:
        # Nulls are also considered invalid references
        orphan_mask = ~child_df[child_column].isin(valid_keys)

    orphan_count = int(orphan_mask.sum())
    orphan_pct = round((orphan_count / total_records) * 100.0, 2)

    sample_orphans: List[Any] = []
    if orphan_count > 0:
        # Collect sample child record identifiers or foreign key values
        if child_id_column and child_id_column in child_df.columns:
            sample_orphans = (
                child_df.loc[orphan_mask, child_id_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )
        else:
            sample_orphans = (
                child_df.loc[orphan_mask, child_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )

        details = (
            f"Found {orphan_count} orphan records ({orphan_pct}%) where "
            f"{child_dataset}.{child_column} is not found in {parent_dataset}.{parent_column}."
        )
        return CheckResult.create(
            dataset=child_dataset,
            check_name=check_name,
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            total_records=total_records,
            failed_records=orphan_count,
            batch_id=batch_id,
            severity=severity,
            details=details,
            sample_failed_records=sample_orphans,
        )

    return CheckResult.create(
        dataset=child_dataset,
        check_name=check_name,
        category=CheckCategory.REFERENTIAL_INTEGRITY,
        total_records=total_records,
        failed_records=0,
        batch_id=batch_id,
        severity=severity,
        details=(
            f"Referential integrity verified: all {total_records:,} records in "
            f"{child_dataset}.{child_column} match valid keys in {parent_dataset}.{parent_column}."
        ),
    )
