
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
# 2. FIND LATEST BRONZE BATCH
# ==========================================

def find_latest_batch():

    batches = [
        folder
        for folder in BRONZE_DIR.iterdir()
        if folder.is_dir()
        and (folder / "ingestion_manifest.json").exists()
    ]

    if not batches:
        raise FileNotFoundError(
            "No Bronze batch found."
        )

    return max(
        batches,
        key=lambda folder: folder.stat().st_mtime
    )


# ==========================================
# 3. LOAD BRANCHES
# ==========================================

def load_branches(source_path):

    print("\n[1] Loading branches from Bronze...")

    df = pd.read_csv(source_path)

    print(f"Loaded records: {len(df):,}")

    return df


# ==========================================
# 4. STANDARDIZATION
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
# 5. DATA QUALITY VALIDATION
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
# 6. BUSINESS TRANSFORMATIONS
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
# 7. SILVER VALIDATION
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
# 8. SAVE SILVER OUTPUTS
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
# 9. MAIN PIPELINE
# ==========================================

def main():

    print("=" * 55)
    print("BRONZE TO SILVER: BRANCHES TRANSFORMATION")
    print("=" * 55)

    bronze_batch = find_latest_batch()

    batch_id = bronze_batch.name

    source_path = bronze_batch / "branches.csv"

    if not source_path.exists():

        raise FileNotFoundError(
            f"Branches file not found: {source_path}"
        )

    silver_batch_dir = SILVER_DIR / batch_id

    # Load
    raw_df = load_branches(source_path)

    input_count = len(raw_df)

    # Standardize
    standardized_df = standardize_branches(raw_df)

    # Validate
    valid_df, quarantine_df = validate_branches(
        standardized_df
    )

    # Business transformations
    silver_df = apply_business_transformations(
        valid_df
    )

    # Validate Silver
    validate_silver(
        silver_df,
        input_count,
        len(quarantine_df)
    )

    # Save outputs
    save_outputs(
        silver_batch_dir,
        silver_df,
        quarantine_df,
        input_count,
        batch_id
    )

    # Summary
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


if __name__ == "__main__":
    main()
