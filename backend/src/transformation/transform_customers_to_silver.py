
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
# 3. LOAD CUSTOMERS
# ==========================================

def load_customers(source_path):

    print("\n[1] Loading customers from Bronze...")

    df = pd.read_csv(source_path)

    print(f"Loaded records: {len(df):,}")

    return df


# ==========================================
# 4. STANDARDIZATION
# ==========================================

def standardize_customers(df):

    print("\n[2] Standardizing customer data...")

    df = df.copy()

    text_columns = [
        "customer_id",
        "customer_name",
        "customer_type",
        "city"
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Standardize customer type
    df["customer_type"] = (
        df["customer_type"].str.title()
    )

    # Standardize city names
    df["city"] = df["city"].str.title()

    # Convert registration date
    df["registration_date"] = pd.to_datetime(
        df["registration_date"],
        errors="coerce"
    )

    return df


# ==========================================
# 5. DATA QUALITY VALIDATION
# ==========================================

def validate_customers(df):

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

    # Required fields validation
    required_columns = [
        "customer_id",
        "customer_name",
        "customer_type",
        "city",
        "registration_date"
    ]

    for column in required_columns:

        add_reason(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    # Primary key validation
    duplicate_ids = (
        df["customer_id"].notna()
        & df["customer_id"].duplicated(keep=False)
    )

    add_reason(
        duplicate_ids,
        "Duplicate customer_id"
    )

    # Allowed customer types
    allowed_types = [
        "Individual",
        "Business"
    ]

    add_reason(
        df["customer_type"].notna()
        & ~df["customer_type"].isin(allowed_types),
        "Invalid customer_type"
    )

    # Future registration dates
    today = pd.Timestamp.now().normalize()

    add_reason(
        df["registration_date"].notna()
        & (df["registration_date"] > today),
        "Future registration_date"
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

    # Calculate customer tenure in days
    df["customer_tenure_days"] = (
        today - df["registration_date"]
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
    assert df["customer_id"].is_unique, (
        "Duplicate customer_id found."
    )

    # Missing values validation
    assert not df.isnull().any().any(), (
        "Missing values found in Silver."
    )

    # Customer type validation
    assert df["customer_type"].isin(
        ["Individual", "Business"]
    ).all(), "Invalid customer_type found."

    # Registration date validation
    today = pd.Timestamp.now().normalize()

    assert (
        df["registration_date"] <= today
    ).all(), "Future registration date found."

    # Customer tenure validation
    expected_tenure = (
        today - df["registration_date"]
    ).dt.days

    assert (
        df["customer_tenure_days"] == expected_tenure
    ).all(), "Customer tenure calculation failed."

    assert (
        df["customer_tenure_days"] >= 0
    ).all(), "Negative customer tenure found."

    print("Record Reconciliation: PASSED")
    print("Primary Key Validation: PASSED")
    print("Missing Values Validation: PASSED")
    print("Customer Type Validation: PASSED")
    print("Registration Date Validation: PASSED")
    print("Customer Tenure Calculation: PASSED")


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

    # Save valid customers
    silver_df.to_csv(
        silver_batch_dir / "customers.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    # Save rejected customers
    quarantine_df.to_csv(
        silver_batch_dir / "customers_quarantine.csv",
        index=False
    )

    # Create transformation manifest
    manifest = {
        "dataset": "customers",
        "source_layer": "bronze",
        "target_layer": "silver",
        "batch_id": batch_id,
        "transformation_timestamp": datetime.now().isoformat(),
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "business_transformations": [
            "customer_tenure_days"
        ],
        "output_files": [
            "customers.csv",
            "customers_quarantine.csv"
        ]
    }

    with open(
        silver_batch_dir
        / "customers_transformation_manifest.json",
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
    print("BRONZE TO SILVER: CUSTOMERS TRANSFORMATION")
    print("=" * 55)

    # Find Bronze batch
    bronze_batch = find_latest_batch()

    batch_id = bronze_batch.name

    source_path = bronze_batch / "customers.csv"

    if not source_path.exists():

        raise FileNotFoundError(
            f"Customers file not found: {source_path}"
        )

    silver_batch_dir = SILVER_DIR / batch_id

    # Step 1: Load
    raw_df = load_customers(source_path)

    input_count = len(raw_df)

    # Step 2: Standardize
    standardized_df = standardize_customers(raw_df)

    # Step 3: Validate
    valid_df, quarantine_df = validate_customers(
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
        "Business Customers:",
        int(
            (silver_df["customer_type"] == "Business").sum()
        )
    )

    print(
        "Individual Customers:",
        int(
            (silver_df["customer_type"] == "Individual").sum()
        )
    )

    print(
        "Unique Cities:",
        silver_df["city"].nunique()
    )

    print(
        "Average Customer Tenure (Days):",
        round(
            silver_df["customer_tenure_days"].mean(),
            2
        )
    )

    print(
        "\nBRONZE TO SILVER CUSTOMERS TRANSFORMATION COMPLETED!"
    )


if __name__ == "__main__":
    main()
