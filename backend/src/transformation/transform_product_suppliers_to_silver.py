
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

REQUIRED_COLUMNS = [
    "product_id",
    "supplier_id",
    "supplier_price",
    "lead_time_days",
    "minimum_order_qty",
    "is_preferred_supplier",
]

PRODUCT_REFERENCE_COLUMNS = ["product_id"]
SUPPLIER_REFERENCE_COLUMNS = ["supplier_id"]

HIGH_LEAD_TIME_THRESHOLD = 10


def load_reference_data(batch_dir):
    silver_batch_dir = SILVER_DIR / batch_dir.name

    products_path = silver_batch_dir / "products.csv"
    suppliers_path = silver_batch_dir / "suppliers.csv"

    if not products_path.exists():
        raise FileNotFoundError(
            f"Missing Silver products: {products_path}"
        )

    if not suppliers_path.exists():
        raise FileNotFoundError(
            f"Missing Silver suppliers: {suppliers_path}"
        )

    products = pd.read_csv(products_path)
    suppliers = pd.read_csv(suppliers_path)

    missing_product_columns = (
        set(PRODUCT_REFERENCE_COLUMNS) - set(products.columns)
    )
    missing_supplier_columns = (
        set(SUPPLIER_REFERENCE_COLUMNS) - set(suppliers.columns)
    )

    if missing_product_columns:
        raise ValueError(
            "Silver products is missing required columns: "
            f"{sorted(missing_product_columns)}"
        )

    if missing_supplier_columns:
        raise ValueError(
            "Silver suppliers is missing required columns: "
            f"{sorted(missing_supplier_columns)}"
        )

    return products, suppliers


def load_product_suppliers(batch_dir):
    path = batch_dir / "product_suppliers.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Product suppliers Bronze file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    return df


def standardize_data(df):
    df = df.copy()

    text_columns = ["product_id", "supplier_id"]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    numeric_columns = [
        "supplier_price",
        "lead_time_days",
        "minimum_order_qty",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df["is_preferred_supplier"] = (
        df["is_preferred_supplier"]
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


def validate_data(df, products, suppliers):
    df = df.copy()
    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(mask, message):
        nonlocal reasons
        reasons.loc[mask] = (
            reasons.loc[mask] + message + "; "
        )

    missing_mask = df[REQUIRED_COLUMNS].isna().any(axis=1)
    add_reason(missing_mask, "Missing or invalid required field")

    duplicate_pairs = (
        df[["product_id", "supplier_id"]].notna().all(axis=1)
        & df.duplicated(
            subset=["product_id", "supplier_id"],
            keep=False
        )
    )
    add_reason(
        duplicate_pairs,
        "Duplicate product-supplier relationship"
    )

    add_reason(
        df["supplier_price"].notna()
        & (df["supplier_price"] <= 0),
        "Supplier price must be greater than zero"
    )

    add_reason(
        df["lead_time_days"].notna()
        & (
            (df["lead_time_days"] <= 0)
            | (df["lead_time_days"] % 1 != 0)
        ),
        "Lead time must be a positive integer"
    )

    add_reason(
        df["minimum_order_qty"].notna()
        & (
            (df["minimum_order_qty"] <= 0)
            | (df["minimum_order_qty"] % 1 != 0)
        ),
        "Minimum order quantity must be a positive integer"
    )

    add_reason(
        df["product_id"].notna()
        & ~df["product_id"].isin(products["product_id"]),
        "Invalid product_id foreign key"
    )

    add_reason(
        df["supplier_id"].notna()
        & ~df["supplier_id"].isin(suppliers["supplier_id"]),
        "Invalid supplier_id foreign key"
    )

    # Every product must have exactly one preferred supplier.
    preferred_counts = (
        df.groupby("product_id", dropna=True)["is_preferred_supplier"]
        .sum()
    )

    invalid_preferred_products = set(
        preferred_counts[
            preferred_counts != 1
        ].index
    )

    invalid_preferred_mask = df["product_id"].isin(
        invalid_preferred_products
    )

    add_reason(
        invalid_preferred_mask,
        "Product must have exactly one preferred supplier"
    )

    valid_mask = reasons.eq("")

    valid_df = df.loc[valid_mask].copy()
    quarantine_df = df.loc[~valid_mask].copy()

    quarantine_df["rejection_reason"] = (
        reasons.loc[~valid_mask].str.rstrip("; ")
    )

    return valid_df, quarantine_df


def apply_business_transformations(df):
    df = df.copy()

    df["supplier_price"] = df["supplier_price"].astype("float64")
    df["lead_time_days"] = df["lead_time_days"].astype("int64")
    df["minimum_order_qty"] = df["minimum_order_qty"].astype("int64")

    supplier_counts = (
        df.groupby("product_id")["supplier_id"]
        .transform("nunique")
    )

    minimum_price = (
        df.groupby("product_id")["supplier_price"]
        .transform("min")
    )

    df["supplier_cost_category"] = "Higher Cost"

    df.loc[
        df["supplier_price"].eq(minimum_price),
        "supplier_cost_category"
    ] = "Lowest Cost"

    df.loc[
        supplier_counts.eq(1),
        "supplier_cost_category"
    ] = "Only Supplier"

    df["is_high_lead_time"] = (
        df["lead_time_days"] > HIGH_LEAD_TIME_THRESHOLD
    )

    return df


def validate_silver(df):
    assert not df.duplicated(
        subset=["product_id", "supplier_id"]
    ).any(), "Duplicate relationships found."

    assert df[REQUIRED_COLUMNS].notna().all().all(), (
        "Null values found in required columns."
    )

    assert (df["supplier_price"] > 0).all()
    assert (df["lead_time_days"] > 0).all()
    assert (df["minimum_order_qty"] > 0).all()

    preferred_counts = (
        df.groupby("product_id")["is_preferred_supplier"].sum()
    )

    assert (preferred_counts == 1).all(), (
        "Each product must have exactly one preferred supplier."
    )

    assert df["supplier_cost_category"].notna().all()
    assert df["is_high_lead_time"].notna().all()

    print("All Silver validation checks passed.")


def save_outputs(valid_df, quarantine_df, source_batch):
    silver_batch_dir = SILVER_DIR / source_batch.name
    silver_batch_dir.mkdir(parents=True, exist_ok=True)

    valid_path = silver_batch_dir / "product_suppliers.csv"
    quarantine_path = (
        silver_batch_dir / "product_suppliers_quarantine.csv"
    )
    manifest_path = (
        silver_batch_dir / "product_suppliers_transformation_manifest.json"
    )

    valid_df.to_csv(valid_path, index=False)
    quarantine_df.to_csv(quarantine_path, index=False)

    manifest = {
        "dataset": "product_suppliers",
        "batch_id": source_batch.name,
        "source_batch_id": source_batch.name,
        "source_batch": source_batch.name,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": len(valid_df) + len(quarantine_df),
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "high_lead_time_threshold_days": HIGH_LEAD_TIME_THRESHOLD,
        "status": "SUCCESS",
        "output_file": valid_path.name,
        "quarantine_file": quarantine_path.name,
    }

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    return manifest


def main(batch_id: str) -> dict:
    if not batch_id or Path(batch_id).name != batch_id:
        raise ValueError(f"Invalid batch_id: {batch_id}")

    print(
        "Starting Product Suppliers Bronze-to-Silver Transformation..."
    )

    source_batch = BRONZE_DIR / batch_id

    if not source_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {source_batch}"
        )

    ingestion_manifest_path = (
        source_batch / "ingestion_manifest.json"
    )

    if not ingestion_manifest_path.exists():
        raise FileNotFoundError(
            f"Missing ingestion manifest: {ingestion_manifest_path}"
        )

    with open(
        ingestion_manifest_path,
        "r",
        encoding="utf-8"
    ) as file:
        json.load(file)

    print(f"Source batch: {source_batch.name}")

    raw_df = load_product_suppliers(source_batch)
    products, suppliers = load_reference_data(source_batch)

    print(f"Input records: {len(raw_df)}")

    df = standardize_data(raw_df)

    valid_df, quarantine_df = validate_data(
        df,
        products,
        suppliers
    )

    silver_df = apply_business_transformations(valid_df)

    validate_silver(silver_df)

    manifest = save_outputs(
        silver_df,
        quarantine_df,
        source_batch
    )

    supplier_categories = {
        str(category): int(count)
        for category, count in (
            silver_df["supplier_cost_category"]
            .value_counts()
            .items()
        )
    }

    high_lead_time_count = int(
        silver_df["is_high_lead_time"].sum()
    )

    preferred_supplier_count = int(
        silver_df["is_preferred_supplier"].sum()
    )

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {manifest['input_records']}")
    print(f"Silver Records: {manifest['silver_records']}")
    print(
        f"Quarantined Records: {manifest['quarantined_records']}"
    )

    print("\nSupplier Cost Categories:")
    print(supplier_categories)

    print("\nHigh Lead Time Relationships:")
    print(high_lead_time_count)

    print("\nPreferred Suppliers:")
    print(preferred_supplier_count)

    print("\nTransformation completed successfully.")

    return {
        "batch_id": batch_id,
        "dataset": "product_suppliers",
        "input_records": int(manifest["input_records"]),
        "silver_records": int(manifest["silver_records"]),
        "quarantined_records": int(
            manifest["quarantined_records"]
        ),
        "supplier_cost_categories": supplier_categories,
        "high_lead_time_relationships": high_lead_time_count,
        "preferred_suppliers": preferred_supplier_count,
        "status": "SUCCESS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform product suppliers from Bronze to Silver."
    )
    parser.add_argument(
        "--batch-id",
        required=True,
        help="Bronze batch ID to process."
    )

    args = parser.parse_args()
    main(args.batch_id)
