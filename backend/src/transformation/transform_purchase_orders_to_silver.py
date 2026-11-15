
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

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

REQUIRED_COLUMNS = [
    "po_id",
    "supplier_id",
    "order_date",
    "expected_delivery_date",
    "status",
]


def load_reference_data(batch_id):
    suppliers_path = SILVER_DIR / batch_id / "suppliers.csv"

    if not suppliers_path.exists():
        raise FileNotFoundError(
            f"Silver suppliers not found: {suppliers_path}"
        )

    suppliers = pd.read_csv(suppliers_path)

    if "supplier_id" not in suppliers.columns:
        raise ValueError(
            "Silver suppliers is missing required column: supplier_id"
        )

    return suppliers


def load_purchase_orders(source_path):
    if not source_path.exists():
        raise FileNotFoundError(
            f"Purchase orders source file not found: {source_path}"
        )

    df = pd.read_csv(source_path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing source columns: {sorted(missing_columns)}"
        )

    return df


def standardize_data(df):
    df = df.copy()

    for column in ["po_id", "supplier_id", "status"]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    df["order_date"] = pd.to_datetime(
        df["order_date"],
        errors="coerce"
    )

    df["expected_delivery_date"] = pd.to_datetime(
        df["expected_delivery_date"],
        errors="coerce"
    )

    return df


def validate_data(df, suppliers):
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
        if column in ["order_date", "expected_delivery_date"]:
            missing_mask = df[column].isna()
        else:
            missing_mask = (
                df[column].isna()
                | df[column].astype("string").str.strip().eq("")
            )

        reject(
            missing_mask,
            f"Missing {column}"
        )

    reject(
        df["po_id"].duplicated(keep=False),
        "Duplicate po_id"
    )

    reject(
        df["supplier_id"].notna()
        & ~df["supplier_id"].isin(set(suppliers["supplier_id"])),
        "Invalid supplier_id"
    )

    reject(
        df["status"].notna()
        & ~df["status"].isin(ALLOWED_STATUSES),
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
        df["expected_delivery_date"].notna()
        & df["order_date"].notna()
        & (
            df["expected_delivery_date"] < df["order_date"]
        ),
        "Expected delivery date before order date"
    )

    reject(
        df["order_date"].notna()
        & (
            (df["order_date"] < pd.Timestamp("2025-01-01"))
            | (df["order_date"] > pd.Timestamp("2025-12-31"))
        ),
        "Order date outside 2025"
    )

    df["rejection_reason"] = rejection_reasons

    valid_df = df[rejection_reasons.eq("")].copy()
    quarantine_df = df[rejection_reasons.ne("")].copy()

    return valid_df, quarantine_df


def apply_business_transformations(valid_df):
    valid_df = valid_df.copy()

    valid_df["days_until_expected_delivery"] = (
        valid_df["expected_delivery_date"]
        - valid_df["order_date"]
    ).dt.days

    valid_df["is_cancelled"] = valid_df["status"].eq("Cancelled")
    valid_df["is_pending"] = valid_df["status"].eq("Pending")
    valid_df["is_fully_received"] = (
        valid_df["status"].eq("Fully Received")
    )
    valid_df["is_partially_received"] = (
        valid_df["status"].eq("Partially Received")
    )

    return valid_df


def validate_silver(valid_df, quarantine_df, input_count, suppliers):
    assert len(valid_df) + len(quarantine_df) == input_count

    assert valid_df["po_id"].is_unique

    assert valid_df[REQUIRED_COLUMNS].notna().all().all()

    assert valid_df["supplier_id"].isin(
        set(suppliers["supplier_id"])
    ).all()

    assert valid_df["status"].isin(ALLOWED_STATUSES).all()

    assert (
        valid_df["expected_delivery_date"]
        >= valid_df["order_date"]
    ).all()

    assert (
        valid_df["order_date"].between(
            pd.Timestamp("2025-01-01"),
            pd.Timestamp("2025-12-31")
        )
    ).all()

    print("\nAll Silver validation checks passed.")


def save_outputs(
    valid_df,
    quarantine_df,
    batch_id,
    input_count
):
    output_dir = SILVER_DIR / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_path = output_dir / "purchase_orders.csv"
    quarantine_path = output_dir / "purchase_orders_quarantine.csv"

    manifest_path = (
        output_dir / "purchase_orders_transformation_manifest.json"
    )

    valid_df.to_csv(
        valid_path,
        index=False,
        date_format="%Y-%m-%d"
    )

    quarantine_df.to_csv(
        quarantine_path,
        index=False,
        date_format="%Y-%m-%d"
    )

    manifest = {
        "dataset": "purchase_orders",
        "batch_id": batch_id,
        "source_batch_id": batch_id,
        "transformation_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_records": int(input_count),
        "silver_records": int(len(valid_df)),
        "quarantined_records": int(len(quarantine_df)),
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
    print("BRONZE TO SILVER: PURCHASE ORDERS")
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

    print(f"\nSource Batch: {batch_id}")

    source_path = bronze_batch / "purchase_orders.csv"

    df = load_purchase_orders(source_path)
    suppliers = load_reference_data(batch_id)

    input_count = len(df)

    print(f"Input Records: {input_count}")

    df = standardize_data(df)

    valid_df, quarantine_df = validate_data(
        df,
        suppliers
    )

    valid_df = apply_business_transformations(valid_df)

    validate_silver(
        valid_df,
        quarantine_df,
        input_count,
        suppliers
    )

    manifest = save_outputs(
        valid_df,
        quarantine_df,
        batch_id,
        input_count
    )

    average_delivery_days = (
        round(
            float(valid_df["days_until_expected_delivery"].mean()),
            2
        )
        if not valid_df.empty
        else None
    )

    status_distribution = {
        str(status): int(count)
        for status, count in valid_df["status"].value_counts().items()
    }

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Input Records: {input_count}")
    print(f"Silver Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")

    if average_delivery_days is not None:
        print(
            "Average Expected Delivery Days:",
            average_delivery_days
        )
    else:
        print("Average Expected Delivery Days: Not available")

    print("\nStatus Distribution:")
    print(status_distribution)

    print("\nTransformation completed successfully!")

    return {
        "batch_id": batch_id,
        "dataset": "purchase_orders",
        "input_records": int(manifest["input_records"]),
        "silver_records": int(manifest["silver_records"]),
        "quarantined_records": int(
            manifest["quarantined_records"]
        ),
        "average_expected_delivery_days": average_delivery_days,
        "status_distribution": status_distribution,
        "status": "SUCCESS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform purchase orders from Bronze to Silver."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Bronze batch ID to process."
    )

    args = parser.parse_args()
    main(args.batch_id)
