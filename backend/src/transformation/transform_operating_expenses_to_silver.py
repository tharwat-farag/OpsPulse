
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json

import pandas as pd


# =========================================================
# 1. PROJECT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_BASE_DIR = PROJECT_ROOT / "data" / "silver"

ALLOWED_CATEGORIES = {
    "Transportation",
    "Rent",
    "Salaries",
    "Maintenance",
    "Electricity",
}


# =========================================================
# 2. TRANSFORMATION
# =========================================================

def main(batch_id: str) -> dict:
    """
    Transform operating expenses from Bronze to Silver.

    Args:
        batch_id: Explicit ingestion batch ID passed by Airflow.

    Returns:
        A summary dictionary containing batch and record counts.
    """

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must be provided.")

    batch_id = batch_id.strip()

    batch_dir = BRONZE_DIR / batch_id
    silver_dir = SILVER_BASE_DIR / batch_id

    manifest_source = batch_dir / "ingestion_manifest.json"
    bronze_file = batch_dir / "operating_expenses.csv"
    branches_file = silver_dir / "branches.csv"

    if not batch_dir.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {batch_dir}"
        )

    if not manifest_source.exists():
        raise FileNotFoundError(
            f"Ingestion manifest not found: {manifest_source}"
        )

    if not bronze_file.exists():
        raise FileNotFoundError(
            f"Bronze operating expenses file not found: {bronze_file}"
        )

    if not branches_file.exists():
        raise FileNotFoundError(
            "Silver branches.csv is required for Branch FK validation."
        )

    silver_dir.mkdir(parents=True, exist_ok=True)

    # =====================================================
    # 3. LOAD SOURCE DATA
    # =====================================================

    df = pd.read_csv(bronze_file, dtype="string")
    branches = pd.read_csv(branches_file, dtype="string")

    input_records = len(df)

    required_columns = [
        "expense_id",
        "branch_id",
        "expense_date",
        "expense_category",
        "amount",
        "description",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required Bronze columns: {missing_columns}"
        )

    if "branch_id" not in branches.columns:
        raise ValueError(
            "Silver branches.csv must contain branch_id."
        )

    print("=" * 60)
    print("OPERATING EXPENSES - BRONZE TO SILVER")
    print("=" * 60)
    print(f"Batch ID: {batch_id}")
    print(f"Input Records: {input_records:,}")

    # =====================================================
    # 4. STANDARDIZATION
    # =====================================================

    text_columns = [
        "expense_id",
        "branch_id",
        "expense_category",
        "description",
    ]

    for column in text_columns:
        df[column] = df[column].str.strip()

    df["expense_category"] = df["expense_category"].str.title()

    df["expense_date"] = pd.to_datetime(
        df["expense_date"],
        errors="coerce",
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    )

    # =====================================================
    # 5. DATA QUALITY VALIDATION
    # =====================================================

    reasons = pd.Series("", index=df.index, dtype="string")

    def reject(condition, reason):
        condition = condition.fillna(False)

        reasons.loc[condition] = (
            reasons.loc[condition]
            + reason
            + "; "
        )

    # Required fields
    for column in required_columns:
        reject(
            df[column].isna() | df[column].eq(""),
            f"Missing or empty {column}",
        )

    # Primary key validation
    reject(
        df["expense_id"].duplicated(keep=False),
        "Duplicate expense_id",
    )

    # Foreign key validation
    valid_branch_ids = set(branches["branch_id"].dropna())

    reject(
        ~df["branch_id"].isin(valid_branch_ids),
        "Invalid branch_id foreign key",
    )

    # Date validation
    reject(
        df["expense_date"].isna(),
        "Invalid expense_date",
    )

    # The generated OpsPulse dataset covers 2025.
    reject(
        df["expense_date"].notna()
        & (df["expense_date"].dt.year != 2025),
        "Expense date outside expected year 2025",
    )

    # Amount validation
    reject(
        df["amount"].isna(),
        "Invalid amount",
    )

    reject(
        df["amount"].notna() & (df["amount"] <= 0),
        "Non-positive amount",
    )

    # Category validation
    reject(
        ~df["expense_category"].isin(ALLOWED_CATEGORIES),
        "Invalid expense_category",
    )

    # =====================================================
    # 6. VALID / QUARANTINE SPLIT
    # =====================================================

    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()
    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask].str.rstrip("; ")
    )

    print("\n[VALIDATION RESULTS]")
    print(f"Valid Records: {len(valid_df):,}")
    print(f"Quarantined Records: {len(quarantine_df):,}")

    # =====================================================
    # 7. SILVER TRANSFORMATIONS
    # =====================================================

    valid_df["expense_date"] = (
        valid_df["expense_date"].dt.normalize()
    )

    valid_df["amount"] = valid_df["amount"].round(2)

    valid_df["expense_year"] = (
        valid_df["expense_date"].dt.year.astype("int64")
    )

    valid_df["expense_month"] = (
        valid_df["expense_date"].dt.month.astype("int64")
    )

    valid_df["expense_quarter"] = (
        "Q"
        + valid_df["expense_date"].dt.quarter.astype("string")
    )

    # =====================================================
    # 8. FINAL DATA QUALITY ASSERTIONS
    # =====================================================

    assert valid_df["expense_id"].is_unique
    assert valid_df["branch_id"].isin(valid_branch_ids).all()
    assert valid_df["amount"].gt(0).all()
    assert valid_df["expense_date"].notna().all()
    assert valid_df["expense_category"].isin(
        ALLOWED_CATEGORIES
    ).all()

    assert (
        len(valid_df) + len(quarantine_df)
        == input_records
    )

    # =====================================================
    # 9. SAVE SILVER OUTPUTS
    # =====================================================

    silver_file = silver_dir / "operating_expenses.csv"

    quarantine_file = (
        silver_dir / "operating_expenses_quarantine.csv"
    )

    manifest_file = (
        silver_dir / "operating_expenses_transformation_manifest.json"
    )

    valid_df.to_csv(silver_file, index=False)
    quarantine_df.to_csv(quarantine_file, index=False)

    # =====================================================
    # 10. SUMMARY AND MANIFEST
    # =====================================================

    category_summary = (
        valid_df.groupby("expense_category")["amount"]
        .agg(["count", "sum", "mean"])
        .round(2)
    )

    total_expenses = round(float(valid_df["amount"].sum()), 2)

    average_expense = (
        round(float(valid_df["amount"].mean()), 2)
        if not valid_df.empty
        else 0.0
    )

    manifest = {
        "dataset": "operating_expenses",
        "batch_id": batch_id,
        "transformation_status": "SUCCESS",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "input_records": input_records,
        "valid_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "quality_checks": {
            "unique_expense_id": True,
            "valid_branch_foreign_keys": True,
            "positive_amounts": True,
            "valid_dates": True,
            "expected_year_2025": True,
            "valid_expense_categories": True,
        },
        "business_metrics": {
            "total_expenses": total_expenses,
            "average_expense": average_expense,
            "expense_categories": int(
                valid_df["expense_category"].nunique()
            ),
            "branches_covered": int(
                valid_df["branch_id"].nunique()
            ),
        },
        "output_file": silver_file.name,
        "quarantine_file": quarantine_file.name,
    }

    with open(manifest_file, "w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # =====================================================
    # 11. FINAL REPORT
    # =====================================================

    print("\n[TRANSFORMATION SUMMARY]")
    print(f"Silver Records: {len(valid_df):,}")
    print(f"Quarantine Records: {len(quarantine_df):,}")

    print(f"Total Expenses: {total_expenses:,.2f} EGP")
    print(f"Average Expense: {average_expense:,.2f} EGP")

    print("\n[EXPENSE SUMMARY BY CATEGORY]")
    print(category_summary.to_string())

    print("\n[OUTPUT FILES]")
    print(f"Silver: {silver_file}")
    print(f"Quarantine: {quarantine_file}")
    print(f"Manifest: {manifest_file}")

    print("\nOPERATING EXPENSES TRANSFORMATION COMPLETED!")

    return {
        "batch_id": batch_id,
        "input_records": input_records,
        "valid_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
    }


# =========================================================
# 12. COMMAND LINE ENTRY POINT
# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform operating expenses from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process.",
    )

    args = parser.parse_args()
    main(args.batch_id)
