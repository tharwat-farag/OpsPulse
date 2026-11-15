
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


REQUIRED_COLUMNS = [
    "po_line_id",
    "po_id",
    "product_id",
    "ordered_qty",
    "unit_cost",
]


def load_reference_data(batch_id):
    silver_batch_dir = SILVER_DIR / batch_id

    purchase_orders_path = silver_batch_dir / "purchase_orders.csv"
    products_path = silver_batch_dir / "products.csv"

    if not purchase_orders_path.exists():
        raise FileNotFoundError(
            f"Silver purchase_orders not found: {purchase_orders_path}"
        )

    if not products_path.exists():
        raise FileNotFoundError(
            f"Silver products not found: {products_path}"
        )

    purchase_orders = pd.read_csv(purchase_orders_path)
    products = pd.read_csv(products_path)

    if "po_id" not in purchase_orders.columns:
        raise ValueError(
            "Silver purchase_orders is missing required column: po_id"
        )

    if "product_id" not in products.columns:
        raise ValueError(
            "Silver products is missing required column: product_id"
        )

    return purchase_orders, products


def load_purchase_order_lines(source_path):
    if not source_path.exists():
        raise FileNotFoundError(
            f"Purchase order lines source file not found: {source_path}"
        )

    df = pd.read_csv(source_path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing columns in purchase_order_lines: "
            f"{sorted(missing_columns)}"
        )

    return df


def standardize_data(df):
    df = df.copy()

    for column in ["po_line_id", "po_id", "product_id"]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    df["ordered_qty"] = pd.to_numeric(
        df["ordered_qty"],
        errors="coerce"
    )

    df["unit_cost"] = pd.to_numeric(
        df["unit_cost"],
        errors="coerce"
    )

    return df


def validate_data(df, purchase_orders, products):
    df = df.copy()

    rejection_reasons = pd.Series(
        "",
        index=df.index,
        dtype="string"
    )

    def reject(mask, reason):
        nonlocal rejection_reasons

        rejection_reasons.loc[mask] = (
            rejection_reasons.loc[mask]
            .apply(
                lambda current:
                f"{current}; {reason}" if current else reason
            )
        )

    for column in REQUIRED_COLUMNS:
        reject(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    reject(
        df["po_line_id"].duplicated(keep=False),
        "Duplicate po_line_id"
    )

    reject(
        df["po_id"].notna()
        & ~df["po_id"].isin(set(purchase_orders["po_id"])),
        "Invalid po_id"
    )

    reject(
        df["product_id"].notna()
        & ~df["product_id"].isin(set(products["product_id"])),
        "Invalid product_id"
    )

    reject(
        df["ordered_qty"].notna()
        & (
            (df["ordered_qty"] <= 0)
            | (df["ordered_qty"] % 1 != 0)
        ),
        "Invalid ordered_qty"
    )

    reject(
        df["unit_cost"].notna()
        & (df["unit_cost"] <= 0),
        "Invalid unit_cost"
    )

    df["rejection_reason"] = rejection_reasons

    valid_df = df[rejection_reasons.eq("")].copy()
    quarantine_df = df[rejection_reasons.ne("")].copy()

    return valid_df, quarantine_df


def apply_business_transformations(valid_df):
    valid_df = valid_df.copy()

    valid_df["ordered_qty"] = (
        valid_df["ordered_qty"].astype("int64")
    )

    valid_df["line_total"] = (
        valid_df["ordered_qty"] * valid_df["unit_cost"]
    ).round(2)

    if valid_df.empty:
        high_value_threshold = None
        valid_df["is_high_value_line"] = pd.Series(
            index=valid_df.index,
            dtype="bool"
        )
    else:
        high_value_threshold = float(
            valid_df["line_total"].quantile(0.75)
        )

        valid_df["is_high_value_line"] = (
            valid_df["line_total"] > high_value_threshold
        )

    return valid_df, high_value_threshold


def validate_silver(
    valid_df,
    quarantine_df,
    input_count,
    purchase_orders,
    products
):
    assert len(valid_df) + len(quarantine_df) == input_count

    assert valid_df["po_line_id"].is_unique

    assert valid_df[REQUIRED_COLUMNS].notna().all().all()

    assert valid_df["po_id"].isin(
        set(purchase_orders["po_id"])
    ).all()

    assert valid_df["product_id"].isin(
        set(products["product_id"])
    ).all()

    assert (valid_df["ordered_qty"] > 0).all()

    assert (valid_df["unit_cost"] > 0).all()

    assert (
        valid_df["line_total"]
        == (
            valid_df["ordered_qty"] * valid_df["unit_cost"]
        ).round(2)
    ).all()

    assert valid_df["is_high_value_line"].notna().all()

    print("\nAll Silver validation checks passed.")


def save_outputs(
    valid_df,
    quarantine_df,
    batch_id,
    input_count,
    high_value_threshold
):
    output_dir = SILVER_DIR / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_path = output_dir / "purchase_order_lines.csv"
    quarantine_path = (
        output_dir / "purchase_order_lines_quarantine.csv"
    )

    manifest_path = (
        output_dir / "purchase_order_lines_transformation_manifest.json"
    )

    valid_df.to_csv(valid_path, index=False)
    quarantine_df.to_csv(quarantine_path, index=False)

    manifest = {
        "dataset": "purchase_order_lines",
        "batch_id": batch_id,
        "source_batch_id": batch_id,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": int(input_count),
        "silver_records": int(len(valid_df)),
        "quarantined_records": int(len(quarantine_df)),
        "high_value_threshold": (
            round(high_value_threshold, 2)
            if high_value_threshold is not None
            else None
        ),
        "status": "SUCCESS",
        "output_file": valid_path.name,
        "quarantine_file": quarantine_path.name,
    }

    with open(
        manifest_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=4)

    return manifest


def main(batch_id: str) -> dict:
    if not batch_id or Path(batch_id).name != batch_id:
        raise ValueError(f"Invalid batch_id: {batch_id}")

    print("=" * 55)
    print("BRONZE TO SILVER: PURCHASE ORDER LINES")
    print("=" * 55)

    bronze_batch = BRONZE_DIR / batch_id

    if not bronze_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {bronze_batch}"
        )

    ingestion_manifest_path = (
        bronze_batch / "ingestion_manifest.json"
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

    source_path = bronze_batch / "purchase_order_lines.csv"

    df = load_purchase_order_lines(source_path)

    purchase_orders, products = load_reference_data(batch_id)

    input_count = len(df)

    print(f"\nSource Batch: {batch_id}")
    print(f"Input Records: {input_count}")

    df = standardize_data(df)

    valid_df, quarantine_df = validate_data(
        df,
        purchase_orders,
        products
    )

    valid_df, high_value_threshold = (
        apply_business_transformations(valid_df)
    )

    validate_silver(
        valid_df,
        quarantine_df,
        input_count,
        purchase_orders,
        products
    )

    manifest = save_outputs(
        valid_df,
        quarantine_df,
        batch_id,
        input_count,
        high_value_threshold
    )

    total_line_value = float(valid_df["line_total"].sum())

    high_value_lines = int(
        valid_df["is_high_value_line"].sum()
    )

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {input_count}")
    print(f"Silver Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")
    print(f"Total PO Line Value: {total_line_value:,.2f} EGP")

    if high_value_threshold is not None:
        print(
            f"High Value Threshold: "
            f"{high_value_threshold:,.2f} EGP"
        )
    else:
        print("High Value Threshold: Not calculated (no valid records)")

    print(f"High Value Lines: {high_value_lines}")

    print("\nTransformation completed successfully!")

    return {
        "batch_id": batch_id,
        "dataset": "purchase_order_lines",
        "input_records": int(manifest["input_records"]),
        "silver_records": int(manifest["silver_records"]),
        "quarantined_records": int(
            manifest["quarantined_records"]
        ),
        "total_line_value": total_line_value,
        "high_value_threshold": high_value_threshold,
        "high_value_lines": high_value_lines,
        "status": "SUCCESS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform purchase order lines from Bronze to Silver."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Bronze batch ID to process."
    )

    args = parser.parse_args()
    main(args.batch_id)
