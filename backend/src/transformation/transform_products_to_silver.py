
import argparse
import json
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


# ==========================================
# 2. LOAD DATA
# ==========================================

def load_products(source_path):
    """Load products from Bronze."""

    print("\n[1] Loading products from Bronze...")

    df = pd.read_csv(source_path)

    print(f"Loaded records: {len(df):,}")

    return df


# ==========================================
# 3. STANDARDIZATION
# ==========================================

def standardize_products(df):
    """Standardize text and convert columns to expected types."""

    print("\n[2] Standardizing product data...")

    df = df.copy()

    text_columns = [
        "product_id",
        "product_name",
        "category",
        "brand",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    numeric_columns = [
        "standard_cost",
        "current_selling_price",
        "reorder_level",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Convert is_active into a consistent Boolean value.
    df["is_active"] = (
        df["is_active"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
        })
    )

    return df


# ==========================================
# 4. DATA QUALITY VALIDATION
# ==========================================

def validate_products(df):
    """Separate valid records from rejected records."""

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
        "product_id",
        "product_name",
        "category",
        "brand",
        "standard_cost",
        "current_selling_price",
        "reorder_level",
        "is_active",
    ]

    for column in required_columns:
        add_reason(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    # Primary key validation
    duplicate_ids = (
        df["product_id"].notna()
        & df["product_id"].duplicated(keep=False)
    )

    add_reason(
        duplicate_ids,
        "Duplicate product_id"
    )

    # Numeric validation
    add_reason(
        df["standard_cost"].notna()
        & (
            ~np.isfinite(df["standard_cost"])
            | (df["standard_cost"] <= 0)
        ),
        "Invalid standard_cost"
    )

    add_reason(
        df["current_selling_price"].notna()
        & (
            ~np.isfinite(df["current_selling_price"])
            | (df["current_selling_price"] <= 0)
        ),
        "Invalid current_selling_price"
    )

    add_reason(
        df["reorder_level"].notna()
        & (
            ~np.isfinite(df["reorder_level"])
            | (df["reorder_level"] < 0)
            | (
                df["reorder_level"]
                != df["reorder_level"].round()
            )
        ),
        "Invalid reorder_level"
    )

    # Split valid and rejected records
    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()

    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = reasons.loc[
        ~valid_mask
    ]

    # Reorder level should be an integer
    valid_df["reorder_level"] = (
        valid_df["reorder_level"].astype("int64")
    )

    print(f"Valid records: {len(valid_df):,}")
    print(f"Quarantined records: {len(quarantine_df):,}")

    return valid_df, quarantine_df


# ==========================================
# 5. BUSINESS TRANSFORMATIONS
# ==========================================

def apply_business_transformations(df):
    """Add useful business-level product attributes."""

    print("\n[4] Applying business transformations...")

    df = df.copy()

    df["standard_unit_margin"] = (
        df["current_selling_price"]
        - df["standard_cost"]
    ).round(2)

    df["is_below_standard_cost"] = (
        df["current_selling_price"]
        < df["standard_cost"]
    )

    return df


# ==========================================
# 6. SILVER VALIDATION
# ==========================================

def validate_silver(df, input_count, quarantine_count):

    print("\n[5] Validating Silver data...")

    assert len(df) + quarantine_count == input_count, (
        "Record reconciliation failed."
    )

    assert df["product_id"].is_unique, (
        "Duplicate product_id found in Silver."
    )

    assert not df.isnull().any().any(), (
        "Missing values found in Silver."
    )

    expected_margin = (
        df["current_selling_price"]
        - df["standard_cost"]
    ).round(2)

    assert np.allclose(
        df["standard_unit_margin"],
        expected_margin
    ), "Margin calculation failed."

    expected_flag = (
        df["current_selling_price"]
        < df["standard_cost"]
    )

    assert (
        df["is_below_standard_cost"]
        == expected_flag
    ).all(), "Business flag validation failed."

    assert (
        df["reorder_level"] >= 0
    ).all(), "Invalid reorder_level in Silver."

    print("Record Reconciliation: PASSED")
    print("Primary Key Validation: PASSED")
    print("Missing Values Validation: PASSED")
    print("Margin Calculation: PASSED")
    print("Business Flag Validation: PASSED")
    print("Reorder Level Validation: PASSED")


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
        silver_batch_dir / "products.csv",
        index=False
    )

    quarantine_df.to_csv(
        silver_batch_dir / "products_quarantine.csv",
        index=False
    )

    manifest = {
        "dataset": "products",
        "source_layer": "bronze",
        "target_layer": "silver",
        "batch_id": batch_id,
        "transformation_timestamp": datetime.now().isoformat(),
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "output_files": [
            "products.csv",
            "products_quarantine.csv"
        ]
    }

    with open(
        silver_batch_dir / "products_transformation_manifest.json",
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
    print("BRONZE TO SILVER: PRODUCTS TRANSFORMATION")
    print("=" * 55)

    # Use the exact batch received from Airflow.
    bronze_batch = BRONZE_DIR / batch_id

    if not bronze_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {bronze_batch}"
        )

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

    source_path = bronze_batch / "products.csv"

    if not source_path.exists():
        raise FileNotFoundError(
            f"Products file not found: {source_path}"
        )

    silver_batch_dir = SILVER_DIR / batch_id

    # Load
    raw_df = load_products(source_path)

    input_count = len(raw_df)

    # Standardize
    standardized_df = standardize_products(raw_df)

    # Validate
    valid_df, quarantine_df = validate_products(
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

    # Save
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
        "Products Below Standard Cost:",
        int(silver_df["is_below_standard_cost"].sum())
    )

    print(
        "Inactive Products:",
        int((~silver_df["is_active"]).sum())
    )

    print("\nBRONZE TO SILVER PRODUCTS TRANSFORMATION COMPLETED!")

    return {
        "batch_id": batch_id,
        "input_records": input_count,
        "valid_records": len(silver_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
    }


# ==========================================
# 9. SCRIPT ENTRY POINT
# ==========================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Transform products from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process."
    )

    args = parser.parse_args()

    main(args.batch_id)
