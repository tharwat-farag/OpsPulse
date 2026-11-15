
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

REQUIRED_COLUMNS = [
    "warehouse_id",
    "warehouse_name",
    "city",
    "region",
    "capacity_units",
    "is_active",
]


# ==========================================
# 2. LOAD WAREHOUSES
# ==========================================

def load_warehouses(batch_dir):

    path = batch_dir / "warehouses.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    return pd.read_csv(path)


# ==========================================
# 3. STANDARDIZATION
# ==========================================

def standardize_data(df):

    df = df.copy()

    text_columns = [
        "warehouse_id",
        "warehouse_name",
        "city",
        "region",
    ]

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    df["capacity_units"] = pd.to_numeric(
        df["capacity_units"],
        errors="coerce"
    )

    df["is_active"] = (
        df["is_active"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
        })
    )

    return df


# ==========================================
# 4. DATA QUALITY VALIDATION
# ==========================================

def validate_data(df):

    df = df.copy()

    reasons = pd.Series(
        "",
        index=df.index,
        dtype="string"
    )

    def add_reason(mask, message):

        nonlocal reasons

        reasons.loc[mask] = (
            reasons.loc[mask]
            + message
            + "; "
        )

    # Required fields
    missing_mask = (
        df[REQUIRED_COLUMNS]
        .isna()
        .any(axis=1)
    )

    add_reason(
        missing_mask,
        "Missing required field"
    )

    # Duplicate warehouse IDs
    duplicate_ids = (
        df["warehouse_id"].notna()
        & df["warehouse_id"].duplicated(keep=False)
    )

    add_reason(
        duplicate_ids,
        "Duplicate warehouse_id"
    )

    # Capacity must be positive
    invalid_capacity = (
        df["capacity_units"].notna()
        & (df["capacity_units"] <= 0)
    )

    add_reason(
        invalid_capacity,
        "Capacity must be greater than zero"
    )

    # Capacity must be an integer
    non_integer_capacity = (
        df["capacity_units"].notna()
        & (df["capacity_units"] % 1 != 0)
    )

    add_reason(
        non_integer_capacity,
        "Capacity must be an integer"
    )

    # Split valid and rejected records
    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()

    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask].str.rstrip("; ")
    )

    return valid_df, quarantine_df


# ==========================================
# 5. BUSINESS TRANSFORMATIONS
# ==========================================

def apply_business_transformations(df):

    df = df.copy()

    df["capacity_units"] = (
        df["capacity_units"].astype("int64")
    )

    df["warehouse_location"] = (
        df["city"] + ", " + df["region"]
    )

    df["warehouse_capacity_category"] = pd.cut(
        df["capacity_units"],
        bins=[0, 6000, 8000, float("inf")],
        labels=["Small", "Medium", "Large"],
        include_lowest=True,
    ).astype("string")

    return df


# ==========================================
# 6. SILVER VALIDATION
# ==========================================

def validate_silver(df):

    assert df["warehouse_id"].is_unique, (
        "Duplicate warehouse IDs found."
    )

    assert df[REQUIRED_COLUMNS].notna().all().all(), (
        "Null values found."
    )

    assert (df["capacity_units"] > 0).all(), (
        "Invalid capacity found."
    )

    assert (df["capacity_units"] % 1 == 0).all(), (
        "Non-integer capacity found."
    )

    assert df["warehouse_location"].notna().all(), (
        "Missing warehouse location found."
    )

    assert df["warehouse_capacity_category"].notna().all(), (
        "Missing warehouse capacity category found."
    )

    print("All Silver validation checks passed.")


# ==========================================
# 7. SAVE SILVER OUTPUTS
# ==========================================

def save_outputs(
    valid_df,
    quarantine_df,
    batch_id
):

    silver_batch_dir = SILVER_DIR / batch_id

    silver_batch_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    valid_path = (
        silver_batch_dir / "warehouses.csv"
    )

    quarantine_path = (
        silver_batch_dir / "warehouses_quarantine.csv"
    )

    manifest_path = (
        silver_batch_dir
        / "warehouses_transformation_manifest.json"
    )

    valid_df.to_csv(
        valid_path,
        index=False
    )

    quarantine_df.to_csv(
        quarantine_path,
        index=False
    )

    manifest = {
        "dataset": "warehouses",
        "batch_id": batch_id,
        "source_batch": batch_id,
        "transformation_timestamp": (
            datetime.now(timezone.utc).isoformat()
        ),
        "input_records": len(valid_df) + len(quarantine_df),
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "output_file": valid_path.name,
        "quarantine_file": quarantine_path.name,
    }

    with open(
        manifest_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            manifest,
            file,
            indent=4
        )

    return manifest


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
    print("BRONZE TO SILVER: WAREHOUSES TRANSFORMATION")
    print("=" * 55)

    # Resolve exact Bronze batch
    source_batch = BRONZE_DIR / batch_id

    if not source_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {source_batch}"
        )

    # Validate ingestion manifest
    ingestion_manifest = (
        source_batch / "ingestion_manifest.json"
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

    print(f"Source batch: {batch_id}")

    # Load
    raw_df = load_warehouses(source_batch)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in raw_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required warehouse columns: {missing_columns}"
        )

    input_count = len(raw_df)

    print(f"Input records: {input_count:,}")

    # Standardize
    df = standardize_data(raw_df)

    # Validate and quarantine
    valid_df, quarantine_df = validate_data(df)

    # Business transformations
    silver_df = apply_business_transformations(
        valid_df
    )

    # Silver validation
    validate_silver(silver_df)

    # Save
    manifest = save_outputs(
        silver_df,
        quarantine_df,
        batch_id
    )

    # Summary
    print("\n=== TRANSFORMATION SUMMARY ===")

    print(f"Batch ID: {batch_id}")
    print(f"Input Records: {manifest['input_records']:,}")
    print(f"Silver Records: {manifest['silver_records']:,}")
    print(f"Quarantined Records: {manifest['quarantined_records']:,}")

    print(
        f"Active Warehouses: {int(silver_df['is_active'].sum())}"
    )

    print(
        "Total Capacity:",
        int(silver_df["capacity_units"].sum())
    )

    print("\nCapacity Categories:")

    print(
        silver_df["warehouse_capacity_category"].value_counts()
    )

    print("\nTransformation completed successfully.")

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
        description="Transform warehouses from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process."
    )

    args = parser.parse_args()

    main(args.batch_id)
