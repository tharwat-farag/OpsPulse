
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

EMAIL_PATTERN = (
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


# ==========================================
# 2. LOAD SUPPLIERS
# ==========================================

def load_suppliers(source_path):

    print("\n[1] Loading suppliers from Bronze...")

    df = pd.read_csv(source_path)

    print(f"Loaded records: {len(df):,}")

    return df


# ==========================================
# 3. STANDARDIZATION
# ==========================================

def standardize_suppliers(df):

    print("\n[2] Standardizing supplier data...")

    df = df.copy()

    text_columns = [
        "supplier_id",
        "supplier_name",
        "city",
        "contact_email"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Standardize city formatting
    df["city"] = df["city"].str.title()

    # Normalize email addresses
    df["contact_email"] = (
        df["contact_email"].str.lower()
    )

    # Convert rating to numeric
    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    # Standardize Boolean values
    df["is_active"] = (
        df["is_active"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False
        })
    )

    return df


# ==========================================
# 4. DATA QUALITY VALIDATION
# ==========================================

def validate_suppliers(df):

    print("\n[3] Applying data quality rules...")

    df = df.copy()

    reasons = pd.Series(
        "",
        index=df.index,
        dtype="string"
    )

    def add_reason(mask, message):

        nonlocal reasons

        reasons.loc[mask] = reasons.loc[mask].apply(
            lambda current: (
                f"{current}; {message}"
                if current
                else message
            )
        )

    # Required fields
    required_columns = [
        "supplier_id",
        "supplier_name",
        "city",
        "contact_email",
        "rating",
        "is_active"
    ]

    for column in required_columns:

        add_reason(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    # Primary key validation
    duplicate_ids = (
        df["supplier_id"].notna()
        & df["supplier_id"].duplicated(keep=False)
    )

    add_reason(
        duplicate_ids,
        "Duplicate supplier_id"
    )

    # Email format validation
    valid_email = df["contact_email"].str.match(
        EMAIL_PATTERN,
        na=False
    )

    add_reason(
        df["contact_email"].notna()
        & ~valid_email,
        "Invalid contact_email format"
    )

    # Duplicate email validation
    duplicate_emails = (
        df["contact_email"].notna()
        & df["contact_email"].duplicated(keep=False)
    )

    add_reason(
        duplicate_emails,
        "Duplicate contact_email"
    )

    # Rating validation
    valid_rating = (
        np.isfinite(df["rating"])
        & df["rating"].between(1, 5)
    )

    add_reason(
        df["rating"].notna()
        & ~valid_rating,
        "Rating must be between 1 and 5"
    )

    # Split valid and rejected records
    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()

    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask]
    )

    print(f"Valid records: {len(valid_df):,}")
    print(f"Quarantined records: {len(quarantine_df):,}")

    return valid_df, quarantine_df


# ==========================================
# 5. BUSINESS TRANSFORMATIONS
# ==========================================

def apply_business_transformations(df):

    print("\n[4] Applying business transformations...")

    df = df.copy()

    # Identify suppliers with low ratings
    df["is_low_rated"] = df["rating"] < 3

    # Classify supplier ratings
    conditions = [
        df["rating"] < 3,
        df["rating"] < 4,
        df["rating"] < 4.5,
        df["rating"] <= 5
    ]

    categories = [
        "Low",
        "Medium",
        "Good",
        "Excellent"
    ]

    df["rating_category"] = np.select(
        conditions,
        categories,
        default="Unknown"
    )

    return df


# ==========================================
# 6. SILVER VALIDATION
# ==========================================

def validate_silver(
    df,
    input_count,
    quarantine_count
):

    print("\n[5] Validating Silver data...")

    # Record reconciliation
    assert (
        len(df) + quarantine_count == input_count
    ), "Record reconciliation failed."

    # Primary key
    assert df["supplier_id"].is_unique, (
        "Duplicate supplier_id found."
    )

    # Email uniqueness
    assert df["contact_email"].is_unique, (
        "Duplicate contact_email found."
    )

    # Missing values
    assert not df.isnull().any().any(), (
        "Missing values found in Silver."
    )

    # Rating validation
    assert df["rating"].between(1, 5).all(), (
        "Invalid supplier rating found."
    )

    # Business flag validation
    expected_flag = df["rating"] < 3

    assert (
        df["is_low_rated"] == expected_flag
    ).all(), "Low rating flag validation failed."

    # Rating category validation
    expected_categories = pd.Series(
        np.select(
            [
                df["rating"] < 3,
                df["rating"] < 4,
                df["rating"] < 4.5,
                df["rating"] <= 5
            ],
            [
                "Low",
                "Medium",
                "Good",
                "Excellent"
            ],
            default="Unknown"
        ),
        index=df.index
    )

    assert (
        df["rating_category"] == expected_categories
    ).all(), "Rating category validation failed."

    print("Record Reconciliation: PASSED")
    print("Primary Key Validation: PASSED")
    print("Email Uniqueness: PASSED")
    print("Missing Values Validation: PASSED")
    print("Rating Validation: PASSED")
    print("Low Rating Flag Validation: PASSED")
    print("Rating Category Validation: PASSED")


# ==========================================
# 7. SAVE SILVER OUTPUTS
# ==========================================

def save_outputs(
    silver_batch_dir,
    silver_df,
    quarantine_df,
    input_count,
    batch_id
):

    print("\n[6] Saving Silver outputs...")

    silver_batch_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    silver_df.to_csv(
        silver_batch_dir / "suppliers.csv",
        index=False
    )

    quarantine_df.to_csv(
        silver_batch_dir / "suppliers_quarantine.csv",
        index=False
    )

    manifest = {
        "dataset": "suppliers",
        "source_layer": "bronze",
        "target_layer": "silver",
        "batch_id": batch_id,
        "transformation_timestamp": datetime.now().isoformat(),
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "business_transformations": [
            "is_low_rated",
            "rating_category"
        ],
        "output_files": [
            "suppliers.csv",
            "suppliers_quarantine.csv"
        ]
    }

    with open(
        silver_batch_dir
        / "suppliers_transformation_manifest.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            manifest,
            file,
            indent=4
        )

    print("Silver files saved successfully.")


# ==========================================
# 8. MAIN PIPELINE
# ==========================================

def main(batch_id: str) -> dict:

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must be provided.")

    batch_id = batch_id.strip()

    if Path(batch_id).name != batch_id:
        raise ValueError("Invalid batch_id.")

    print("=" * 55)
    print("BRONZE TO SILVER: SUPPLIERS TRANSFORMATION")
    print("=" * 55)

    # Use the exact batch received from Airflow
    bronze_batch = BRONZE_DIR / batch_id

    if not bronze_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {bronze_batch}"
        )

    # Validate ingestion manifest
    ingestion_manifest = (
        bronze_batch / "ingestion_manifest.json"
    )

    if not ingestion_manifest.exists():
        raise FileNotFoundError(
            f"Ingestion manifest not found: {ingestion_manifest}"
        )

    with open(
        ingestion_manifest,
        "r",
        encoding="utf-8"
    ) as file:

        source_manifest = json.load(file)

    if source_manifest.get("batch_id") != batch_id:
        raise ValueError(
            "Ingestion manifest batch_id does not match requested batch_id."
        )

    source_path = bronze_batch / "suppliers.csv"

    if not source_path.exists():

        raise FileNotFoundError(
            f"Suppliers file not found: {source_path}"
        )

    silver_batch_dir = SILVER_DIR / batch_id

    # Step 1: Load
    raw_df = load_suppliers(source_path)

    required_columns = [
        "supplier_id",
        "supplier_name",
        "city",
        "contact_email",
        "rating",
        "is_active"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in raw_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required supplier columns: {missing_columns}"
        )

    input_count = len(raw_df)

    # Step 2: Standardize
    standardized_df = standardize_suppliers(raw_df)

    # Step 3: Validate
    valid_df, quarantine_df = validate_suppliers(
        standardized_df
    )

    # Step 4: Business transformations
    silver_df = apply_business_transformations(
        valid_df
    )

    # Step 5: Validate Silver
    validate_silver(
        silver_df,
        input_count,
        len(quarantine_df)
    )

    # Step 6: Save
    save_outputs(
        silver_batch_dir,
        silver_df,
        quarantine_df,
        input_count,
        batch_id
    )

    # Step 7: Summary
    print("\n" + "=" * 55)
    print("TRANSFORMATION SUMMARY")
    print("=" * 55)

    print(f"Batch ID: {batch_id}")
    print(f"Input Records: {input_count:,}")
    print(f"Valid Records: {len(silver_df):,}")
    print(f"Quarantined Records: {len(quarantine_df):,}")

    print(
        "Active Suppliers:",
        int(silver_df["is_active"].sum())
    )

    print(
        "Inactive Suppliers:",
        int((~silver_df["is_active"]).sum())
    )

    print(
        "Low-Rated Suppliers:",
        int(silver_df["is_low_rated"].sum())
    )

    print("\nRating Categories:")
    print(silver_df["rating_category"].value_counts())

    print(
        "\nBRONZE TO SILVER SUPPLIERS TRANSFORMATION COMPLETED!"
    )

    return {
        "batch_id": batch_id,
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS"
    }


# ==========================================
# 9. SCRIPT ENTRY POINT
# ==========================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Transform suppliers from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process."
    )

    args = parser.parse_args()

    main(args.batch_id)
