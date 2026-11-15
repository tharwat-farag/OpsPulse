
import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


# ==========================================
# 2. LOAD BRANCHES
# ==========================================

def load_branches(source_path):

    print("\n[1] Loading branches from Bronze...")

    df = pd.read_csv(source_path)

    print(f"Loaded records: {len(df):,}")

    return df


# ==========================================
# 3. STANDARDIZATION
# ==========================================

def standardize_branches(df):

    print("\n[2] Standardizing branch data...")

    df = df.copy()

    text_columns = [
        "branch_id",
        "branch_name",
        "city",
        "region",
        "manager_name"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Standardize text formatting
    for column in [
        "branch_name",
        "city",
        "region",
        "manager_name"
    ]:

        df[column] = df[column].str.title()

    # Convert opening date
    df["opening_date"] = pd.to_datetime(
        df["opening_date"],
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

def validate_branches(df):

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
        "branch_id",
        "branch_name",
        "city",
        "region",
        "manager_name",
        "opening_date",
        "is_active"
    ]

    for column in required_columns:

        add_reason(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    # Primary key validation
    duplicate_ids = (
        df["branch_id"].notna()
        & df["branch_id"].duplicated(keep=False)
    )

    add_reason(
        duplicate_ids,
        "Duplicate branch_id"
    )

    # Future opening dates
    today = pd.Timestamp.now().normalize()

    add_reason(
        df["opening_date"].notna()
        & (df["opening_date"] > today),
        "Future opening_date"
    )

    # Separate valid and rejected records
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

    today = pd.Timestamp.now().normalize()

    df["branch_age_days"] = (
        today - df["opening_date"]
    ).dt.days

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

    # Primary key validation
    assert df["branch_id"].is_unique, (
        "Duplicate branch_id found."
    )

    # Missing values
    assert not df.isnull().any().any(), (
        "Missing values found in Silver."
    )

    # Boolean validation
    assert df["is_active"].map(
        lambda value: isinstance(value, bool)
    ).all(), "Invalid is_active value."

    # Opening date validation
    today = pd.Timestamp.now().normalize()

    assert (
        df["opening_date"] <= today
    ).all(), "Future opening date found."

    # Branch age validation
    expected_age = (
        today - df["opening_date"]
    ).dt.days

    assert (
        df["branch_age_days"] == expected_age
    ).all(), "Branch age calculation failed."

    assert (
        df["branch_age_days"] >= 0
    ).all(), "Negative branch age found."

    print("Record Reconciliation: PASSED")
    print("Primary Key Validation: PASSED")
    print("Missing Values Validation: PASSED")
    print("Boolean Validation: PASSED")
    print("Opening Date Validation: PASSED")
    print("Branch Age Calculation: PASSED")


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

    # Save valid branches
    silver_df.to_csv(
        silver_batch_dir / "branches.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    # Save rejected branches
    quarantine_df.to_csv(
        silver_batch_dir / "branches_quarantine.csv",
        index=False
    )

    # Transformation manifest
    manifest = {
        "dataset": "branches",
        "source_layer": "bronze",
        "target_layer": "silver",
        "batch_id": batch_id,
        "transformation_timestamp": datetime.now().isoformat(),
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "business_transformations": [
            "branch_age_days"
        ],
        "output_files": [
            "branches.csv",
            "branches_quarantine.csv"
        ]
    }

    with open(
        silver_batch_dir
        / "branches_transformation_manifest.json",
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
    print("BRONZE TO SILVER: BRANCHES TRANSFORMATION")
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

    source_path = bronze_batch / "branches.csv"

    if not source_path.exists():

        raise FileNotFoundError(
            f"Branches file not found: {source_path}"
        )

    silver_batch_dir = SILVER_DIR / batch_id

    # Step 1: Load
    raw_df = load_branches(source_path)

    required_columns = [
        "branch_id",
        "branch_name",
        "city",
        "region",
        "manager_name",
        "opening_date",
        "is_active"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in raw_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required branch columns: {missing_columns}"
        )

    input_count = len(raw_df)

    # Step 2: Standardize
    standardized_df = standardize_branches(raw_df)

    # Step 3: Validate
    valid_df, quarantine_df = validate_branches(
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

    # Step 6: Save outputs
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
        "Active Branches:",
        int(silver_df["is_active"].sum())
    )

    print(
        "Inactive Branches:",
        int((~silver_df["is_active"]).sum())
    )

    print(
        "Unique Regions:",
        silver_df["region"].nunique()
    )

    print(
        "Average Branch Age (Days):",
        round(silver_df["branch_age_days"].mean(), 2)
    )

    print(
        "\nBRONZE TO SILVER BRANCHES TRANSFORMATION COMPLETED!"
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
        description="Transform branches from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process."
    )

    args = parser.parse_args()

    main(args.batch_id)
