
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "backend" / "src" / "data_generation")
)

from config import RAW_DATA_DIR  # noqa: E402

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


def find_latest_batch():
    batches = [
        path for path in BRONZE_DIR.iterdir()
        if path.is_dir()
        and (path / "ingestion_manifest.json").exists()
    ]

    if not batches:
        raise FileNotFoundError("No Bronze batch found.")

    return max(batches, key=lambda path: path.stat().st_mtime)


def load_warehouses(batch_dir):
    path = batch_dir / "warehouses.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return pd.read_csv(path)


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


def validate_data(df):
    df = df.copy()
    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(mask, message):
        nonlocal reasons
        reasons.loc[mask] = (
            reasons.loc[mask]
            + message
            + "; "
        )

    missing_mask = df[REQUIRED_COLUMNS].isna().any(axis=1)
    add_reason(missing_mask, "Missing required field")

    duplicate_ids = (
        df["warehouse_id"].notna()
        & df["warehouse_id"].duplicated(keep=False)
    )
    add_reason(duplicate_ids, "Duplicate warehouse_id")

    invalid_capacity = (
        df["capacity_units"].notna()
        & (df["capacity_units"] <= 0)
    )
    add_reason(invalid_capacity, "Capacity must be greater than zero")

    non_integer_capacity = (
        df["capacity_units"].notna()
        & (df["capacity_units"] % 1 != 0)
    )
    add_reason(non_integer_capacity, "Capacity must be an integer")

    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()
    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask].str.rstrip("; ")
    )

    return valid_df, quarantine_df


def apply_business_transformations(df):
    df = df.copy()

    df["capacity_units"] = df["capacity_units"].astype("int64")

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


def validate_silver(df):
    assert df["warehouse_id"].is_unique, "Duplicate warehouse IDs found."
    assert df[REQUIRED_COLUMNS].notna().all().all(), "Null values found."
    assert (df["capacity_units"] > 0).all(), "Invalid capacity found."
    assert (df["capacity_units"] % 1 == 0).all(), "Non-integer capacity found."
    assert df["warehouse_location"].notna().all()
    assert df["warehouse_capacity_category"].notna().all()

    print("All Silver validation checks passed.")


def save_outputs(valid_df, quarantine_df, source_batch):
    silver_batch_dir = SILVER_DIR / source_batch.name
    silver_batch_dir.mkdir(parents=True, exist_ok=True)

    valid_path = silver_batch_dir / "warehouses.csv"
    quarantine_path = silver_batch_dir / "warehouses_quarantine.csv"
    manifest_path = silver_batch_dir / "warehouses_transformation_manifest.json"

    valid_df.to_csv(valid_path, index=False)
    quarantine_df.to_csv(quarantine_path, index=False)

    manifest = {
        "dataset": "warehouses",
        "source_batch": source_batch.name,
        "transformation_timestamp": datetime.now(timezone.utc).isoformat(),
        "input_records": len(valid_df) + len(quarantine_df),
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "output_file": valid_path.name,
        "quarantine_file": quarantine_path.name,
    }

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    return manifest


def main():
    print("Starting Warehouses Bronze-to-Silver Transformation...")

    source_batch = find_latest_batch()
    print(f"Source batch: {source_batch.name}")

    raw_df = load_warehouses(source_batch)
    print(f"Input records: {len(raw_df)}")

    df = standardize_data(raw_df)

    valid_df, quarantine_df = validate_data(df)

    silver_df = apply_business_transformations(valid_df)

    validate_silver(silver_df)

    manifest = save_outputs(
        silver_df,
        quarantine_df,
        source_batch
    )

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {manifest['input_records']}")
    print(f"Silver Records: {manifest['silver_records']}")
    print(f"Quarantined Records: {manifest['quarantined_records']}")
    print(f"Active Warehouses: {silver_df['is_active'].sum()}")
    print(
        "Total Capacity:",
        silver_df["capacity_units"].sum()
    )
    print("\nCapacity Categories:")
    print(silver_df["warehouse_capacity_category"].value_counts())

    print("\nTransformation completed successfully.")


if __name__ == "__main__":
    main()
