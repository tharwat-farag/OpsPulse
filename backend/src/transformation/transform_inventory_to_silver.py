
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

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

REQUIRED_COLUMNS = [
    "inventory_snapshot_id",
    "product_id",
    "warehouse_id",
    "snapshot_date",
    "quantity_on_hand",
    "quantity_reserved",
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


def load_reference_data(batch_dir):
    silver_batch = SILVER_DIR / batch_dir.name

    products_path = silver_batch / "products.csv"
    warehouses_path = silver_batch / "warehouses.csv"

    if not products_path.exists():
        raise FileNotFoundError(f"Missing Products Silver file: {products_path}")

    if not warehouses_path.exists():
        raise FileNotFoundError(f"Missing Warehouses Silver file: {warehouses_path}")

    products = pd.read_csv(products_path)
    warehouses = pd.read_csv(warehouses_path)

    return products, warehouses


def load_inventory(batch_dir):
    path = batch_dir / "inventory.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing inventory file: {path}")

    return pd.read_csv(path)


def standardize_data(df):
    df = df.copy()

    text_columns = [
        "inventory_snapshot_id",
        "product_id",
        "warehouse_id",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    df["snapshot_date"] = pd.to_datetime(
        df["snapshot_date"],
        errors="coerce"
    )

    numeric_columns = [
        "quantity_on_hand",
        "quantity_reserved",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


def validate_data(df, products, warehouses):
    df = df.copy()

    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(mask, message):
        nonlocal reasons
        reasons.loc[mask] = (
            reasons.loc[mask] + message + "; "
        )

    # Required fields
    missing_mask = df[REQUIRED_COLUMNS].isna().any(axis=1)
    add_reason(missing_mask, "Missing or invalid required field")

    # Primary key
    duplicate_ids = (
        df["inventory_snapshot_id"].notna()
        & df["inventory_snapshot_id"].duplicated(keep=False)
    )
    add_reason(duplicate_ids, "Duplicate inventory_snapshot_id")

    # Composite grain
    duplicate_grain = (
        df[
            ["product_id", "warehouse_id", "snapshot_date"]
        ].notna().all(axis=1)
        & df.duplicated(
            subset=[
                "product_id",
                "warehouse_id",
                "snapshot_date",
            ],
            keep=False,
        )
    )
    add_reason(
        duplicate_grain,
        "Duplicate product-warehouse-snapshot_date combination"
    )

    # Foreign keys
    add_reason(
        df["product_id"].notna()
        & ~df["product_id"].isin(products["product_id"]),
        "Invalid product_id foreign key"
    )

    add_reason(
        df["warehouse_id"].notna()
        & ~df["warehouse_id"].isin(warehouses["warehouse_id"]),
        "Invalid warehouse_id foreign key"
    )

    # Quantities must be non-negative integers
    for column in ["quantity_on_hand", "quantity_reserved"]:
        invalid_quantity = (
            df[column].notna()
            & (
                (df[column] < 0)
                | (df[column] % 1 != 0)
            )
        )
        add_reason(
            invalid_quantity,
            f"{column} must be a non-negative integer"
        )

    # Business rule: reserved cannot exceed on-hand
    # We retain these as operational exceptions, not quarantine.
    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()
    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask].str.rstrip("; ")
    )

    return valid_df, quarantine_df


def apply_business_transformations(
    df,
    products,
    warehouses
):
    df = df.copy()

    # Add product standard cost
    product_costs = products[
        ["product_id", "standard_cost"]
    ].copy()

    product_costs["standard_cost"] = pd.to_numeric(
        product_costs["standard_cost"],
        errors="coerce"
    )

    df = df.merge(
        product_costs,
        on="product_id",
        how="left",
        validate="many_to_one"
    )

    # Add warehouse capacity
    warehouse_capacity = warehouses[
        ["warehouse_id", "capacity_units"]
    ].copy()

    warehouse_capacity["capacity_units"] = pd.to_numeric(
        warehouse_capacity["capacity_units"],
        errors="coerce"
    )

    df = df.merge(
        warehouse_capacity,
        on="warehouse_id",
        how="left",
        validate="many_to_one"
    )

    # Available stock
    df["available_quantity"] = (
        df["quantity_on_hand"] - df["quantity_reserved"]
    )

    # Inventory indicators
    df["is_stockout"] = df["quantity_on_hand"].eq(0)

    df["is_fully_reserved"] = (
        df["available_quantity"].eq(0)
    )

    df["is_reserved_exceeds_on_hand"] = (
        df["quantity_reserved"] > df["quantity_on_hand"]
    )

    # Inventory valuation
    df["total_inventory_value"] = (
        df["quantity_on_hand"] * df["standard_cost"]
    )

    df["available_inventory_value"] = (
        df["available_quantity"] * df["standard_cost"]
    )

    df["reserved_inventory_value"] = (
        df["quantity_reserved"] * df["standard_cost"]
    )

    # Calculate warehouse utilization per snapshot date.
    warehouse_daily = (
        df.groupby(
            ["warehouse_id", "snapshot_date"],
            as_index=False
        )
        .agg(
            warehouse_total_on_hand=(
                "quantity_on_hand",
                "sum"
            ),
            capacity_units=(
                "capacity_units",
                "first"
            )
        )
    )

    warehouse_daily["capacity_utilization_pct"] = (
        warehouse_daily["warehouse_total_on_hand"]
        / warehouse_daily["capacity_units"]
        * 100
    )

    # Merge the same warehouse/date utilization onto each product row.
    df = df.merge(
        warehouse_daily[
            [
                "warehouse_id",
                "snapshot_date",
                "warehouse_total_on_hand",
                "capacity_utilization_pct",
            ]
        ],
        on=["warehouse_id", "snapshot_date"],
        how="left",
        validate="many_to_one"
    )

    return df


def validate_silver(df):
    assert df["inventory_snapshot_id"].is_unique
    assert not df.duplicated(
        subset=[
            "product_id",
            "warehouse_id",
            "snapshot_date",
        ]
    ).any()

    assert df[REQUIRED_COLUMNS].notna().all().all()

    assert (df["quantity_on_hand"] >= 0).all()
    assert (df["quantity_reserved"] >= 0).all()

    assert (
        df["available_quantity"]
        == df["quantity_on_hand"] - df["quantity_reserved"]
    ).all()

    assert (
        df["total_inventory_value"]
        == df["quantity_on_hand"] * df["standard_cost"]
    ).all()

    assert df["capacity_utilization_pct"].notna().all()

    print("All Silver validation checks passed.")


def save_outputs(valid_df, quarantine_df, source_batch):
    silver_batch_dir = SILVER_DIR / source_batch.name
    silver_batch_dir.mkdir(parents=True, exist_ok=True)

    valid_path = silver_batch_dir / "inventory.csv"
    quarantine_path = silver_batch_dir / "inventory_quarantine.csv"

    manifest_path = (
        silver_batch_dir / "inventory_transformation_manifest.json"
    )

    valid_df.to_csv(valid_path, index=False)
    quarantine_df.to_csv(quarantine_path, index=False)

    manifest = {
        "dataset": "inventory",
        "source_batch": source_batch.name,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": len(valid_df) + len(quarantine_df),
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
        "output_file": valid_path.name,
        "quarantine_file": quarantine_path.name,
        "business_rules": {
            "available_quantity": "quantity_on_hand - quantity_reserved",
            "total_inventory_value": "quantity_on_hand * standard_cost",
            "available_inventory_value": "available_quantity * standard_cost",
            "capacity_utilization": (
                "warehouse total on-hand / warehouse capacity * 100"
            ),
            "reserved_exceeds_on_hand": (
                "Retained as operational exception, not quarantined"
            ),
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    return manifest


def main():
    print("Starting Inventory Bronze-to-Silver Transformation...")

    source_batch = find_latest_batch()
    print(f"Source batch: {source_batch.name}")

    raw_df = load_inventory(source_batch)
    products, warehouses = load_reference_data(source_batch)

    print(f"Input records: {len(raw_df)}")

    df = standardize_data(raw_df)

    valid_df, quarantine_df = validate_data(
        df,
        products,
        warehouses
    )

    silver_df = apply_business_transformations(
        valid_df,
        products,
        warehouses
    )

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

    print(
        "Stockout Records:",
        silver_df["is_stockout"].sum()
    )

    print(
        "Fully Reserved Records:",
        silver_df["is_fully_reserved"].sum()
    )

    print(
        "Reserved Exceeds On-Hand:",
        silver_df["is_reserved_exceeds_on_hand"].sum()
    )

    print(
        "Total Inventory Value:",
        round(silver_df["total_inventory_value"].sum(), 2)
    )

    print(
        "Available Inventory Value:",
        round(silver_df["available_inventory_value"].sum(), 2)
    )

    print("\nAverage Capacity Utilization by Warehouse:")
    print(
        silver_df.groupby("warehouse_id")[
            "capacity_utilization_pct"
        ].mean().round(2)
    )

    print("\nTransformation completed successfully.")


if __name__ == "__main__":
    main()
