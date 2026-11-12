
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


def find_latest_batch():
    batches = [
        path for path in BRONZE_DIR.iterdir()
        if path.is_dir() and (path / "ingestion_manifest.json").exists()
    ]

    if not batches:
        raise FileNotFoundError("No Bronze batch found.")

    return max(batches, key=lambda path: path.stat().st_mtime)


def main():
    print("=" * 55)
    print("BRONZE TO SILVER: PURCHASE ORDER LINES")
    print("=" * 55)

    bronze_batch = find_latest_batch()
    batch_id = bronze_batch.name

    source_path = bronze_batch / "purchase_order_lines.csv"
    purchase_orders_path = SILVER_DIR / batch_id / "purchase_orders.csv"
    products_path = SILVER_DIR / batch_id / "products.csv"

    if not purchase_orders_path.exists():
        raise FileNotFoundError("Silver purchase_orders not found.")

    if not products_path.exists():
        raise FileNotFoundError("Silver products not found.")

    df = pd.read_csv(source_path)
    purchase_orders = pd.read_csv(purchase_orders_path)
    products = pd.read_csv(products_path)

    input_count = len(df)

    print(f"\nSource Batch: {batch_id}")
    print(f"Input Records: {input_count}")

    required_columns = [
        "po_line_id",
        "po_id",
        "product_id",
        "ordered_qty",
        "unit_cost",
    ]

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    # Standardization
    for column in ["po_line_id", "po_id", "product_id"]:
        df[column] = df[column].astype("string").str.strip()

    df["ordered_qty"] = pd.to_numeric(
        df["ordered_qty"], errors="coerce"
    )

    df["unit_cost"] = pd.to_numeric(
        df["unit_cost"], errors="coerce"
    )

    # Data Quality Rules
    rejection_reasons = pd.Series("", index=df.index, dtype="string")

    def reject(mask, reason):
        nonlocal rejection_reasons
        rejection_reasons.loc[mask] = (
            rejection_reasons.loc[mask]
            .apply(
                lambda current:
                f"{current}; {reason}" if current else reason
            )
        )

    for column in required_columns:
        reject(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    reject(
        df["po_line_id"].duplicated(keep=False),
        "Duplicate po_line_id"
    )

    reject(
        ~df["po_id"].isin(set(purchase_orders["po_id"])),
        "Invalid po_id"
    )

    reject(
        ~df["product_id"].isin(set(products["product_id"])),
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
        df["unit_cost"].notna() & (df["unit_cost"] <= 0),
        "Invalid unit_cost"
    )

    df["rejection_reason"] = rejection_reasons

    valid_df = df[rejection_reasons.eq("")].copy()
    quarantine_df = df[rejection_reasons.ne("")].copy()

    # Business Transformation
    valid_df["ordered_qty"] = valid_df["ordered_qty"].astype("int64")

    valid_df["line_total"] = (
        valid_df["ordered_qty"] * valid_df["unit_cost"]
    ).round(2)

    high_value_threshold = valid_df["line_total"].quantile(0.75)

    valid_df["is_high_value_line"] = (
        valid_df["line_total"] > high_value_threshold
    )

    # Silver Validation
    assert len(valid_df) + len(quarantine_df) == input_count
    assert valid_df["po_line_id"].is_unique
    assert valid_df[required_columns].notna().all().all()
    assert valid_df["po_id"].isin(set(purchase_orders["po_id"])).all()
    assert valid_df["product_id"].isin(set(products["product_id"])).all()
    assert (valid_df["ordered_qty"] > 0).all()
    assert (valid_df["unit_cost"] > 0).all()
    assert (
        valid_df["line_total"]
        == (valid_df["ordered_qty"] * valid_df["unit_cost"]).round(2)
    ).all()

    print("\nAll Silver validation checks passed.")

    # Save Outputs
    output_dir = SILVER_DIR / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_df.to_csv(
        output_dir / "purchase_order_lines.csv",
        index=False
    )

    quarantine_df.to_csv(
        output_dir / "purchase_order_lines_quarantine.csv",
        index=False
    )

    manifest = {
        "dataset": "purchase_order_lines",
        "source_batch_id": batch_id,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": input_count,
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "high_value_threshold": round(float(high_value_threshold), 2),
        "status": "SUCCESS",
    }

    with open(
        output_dir / "purchase_order_lines_transformation_manifest.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=4)

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {input_count}")
    print(f"Silver Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")
    print(f"Total PO Line Value: {valid_df['line_total'].sum():,.2f} EGP")
    print(f"High Value Threshold: {high_value_threshold:,.2f} EGP")
    print(
        "High Value Lines:",
        int(valid_df["is_high_value_line"].sum())
    )

    print("\nTransformation completed successfully!")


if __name__ == "__main__":
    main()
