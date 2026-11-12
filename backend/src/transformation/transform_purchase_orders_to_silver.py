
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

ALLOWED_STATUSES = {
    "Partially Received",
    "Fully Received",
    "Cancelled",
    "Pending",
}


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
    print("BRONZE TO SILVER: PURCHASE ORDERS")
    print("=" * 55)

    bronze_batch = find_latest_batch()
    batch_id = bronze_batch.name

    print(f"\nSource Batch: {batch_id}")

    source_path = bronze_batch / "purchase_orders.csv"
    suppliers_path = SILVER_DIR / batch_id / "suppliers.csv"

    if not suppliers_path.exists():
        raise FileNotFoundError(
            f"Silver suppliers not found: {suppliers_path}"
        )

    df = pd.read_csv(source_path)
    suppliers = pd.read_csv(suppliers_path)

    input_count = len(df)

    print(f"Input Records: {input_count}")

    required_columns = [
        "po_id",
        "supplier_id",
        "order_date",
        "expected_delivery_date",
        "status",
    ]

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing source columns: {missing_columns}")

    # Standardization
    for column in ["po_id", "supplier_id", "status"]:
        df[column] = df[column].astype("string").str.strip()

    df["order_date"] = pd.to_datetime(
        df["order_date"], errors="coerce"
    )

    df["expected_delivery_date"] = pd.to_datetime(
        df["expected_delivery_date"], errors="coerce"
    )

    # Data Quality Checks
    rejection_reasons = pd.Series("", index=df.index, dtype="string")

    def reject(mask, reason):
        nonlocal rejection_reasons
        rejection_reasons.loc[mask] = (
            rejection_reasons.loc[mask]
            .apply(lambda current: f"{current}; {reason}" if current else reason)
        )

    for column in required_columns:
        reject(
            df[column].isna() | df[column].astype("string").str.strip().eq(""),
            f"Missing {column}"
        )

    reject(
        df["po_id"].duplicated(keep=False),
        "Duplicate po_id"
    )

    reject(
        ~df["supplier_id"].isin(set(suppliers["supplier_id"])),
        "Invalid supplier_id"
    )

    reject(
        ~df["status"].isin(ALLOWED_STATUSES),
        "Invalid status"
    )

    reject(
        df["order_date"].isna(),
        "Invalid order_date"
    )

    reject(
        df["expected_delivery_date"].isna(),
        "Invalid expected_delivery_date"
    )

    reject(
        df["expected_delivery_date"] < df["order_date"],
        "Expected delivery date before order date"
    )

    reject(
        (df["order_date"] < pd.Timestamp("2025-01-01"))
        | (df["order_date"] > pd.Timestamp("2025-12-31")),
        "Order date outside 2025"
    )

    df["rejection_reason"] = rejection_reasons

    valid_df = df[rejection_reasons.eq("")].copy()
    quarantine_df = df[rejection_reasons.ne("")].copy()

    # Business Transformations
    valid_df["days_until_expected_delivery"] = (
        valid_df["expected_delivery_date"] - valid_df["order_date"]
    ).dt.days

    valid_df["is_cancelled"] = valid_df["status"].eq("Cancelled")
    valid_df["is_pending"] = valid_df["status"].eq("Pending")
    valid_df["is_fully_received"] = valid_df["status"].eq("Fully Received")
    valid_df["is_partially_received"] = valid_df["status"].eq(
        "Partially Received"
    )

    # Silver Validation
    assert len(valid_df) + len(quarantine_df) == input_count
    assert valid_df["po_id"].is_unique
    assert valid_df[required_columns].notna().all().all()
    assert valid_df["supplier_id"].isin(set(suppliers["supplier_id"])).all()
    assert valid_df["status"].isin(ALLOWED_STATUSES).all()
    assert (
        valid_df["expected_delivery_date"] >= valid_df["order_date"]
    ).all()

    print("\nAll Silver validation checks passed.")

    # Save Outputs
    output_dir = SILVER_DIR / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_df.to_csv(
        output_dir / "purchase_orders.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    quarantine_df.to_csv(
        output_dir / "purchase_orders_quarantine.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    manifest = {
        "dataset": "purchase_orders",
        "source_batch_id": batch_id,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": input_count,
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "status": "SUCCESS",
    }

    with open(
        output_dir / "purchase_orders_transformation_manifest.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=4)

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {input_count}")
    print(f"Silver Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")
    print(
        "Average Expected Delivery Days:",
        round(valid_df["days_until_expected_delivery"].mean(), 2)
    )

    print("\nStatus Distribution:")
    print(valid_df["status"].value_counts())

    print("\nTransformation completed successfully!")


if __name__ == "__main__":
    main()
