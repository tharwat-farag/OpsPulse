
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


# =========================================================
# MAIN TRANSFORMATION
# =========================================================

def main(batch_id: str) -> dict:

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must be provided.")

    batch_id = batch_id.strip()

    if Path(batch_id).name != batch_id:
        raise ValueError("Invalid batch_id.")

    print("=" * 55)
    print("BRONZE TO SILVER: GOODS RECEIPTS")
    print("=" * 55)

    # Resolve exact Bronze batch
    bronze_batch = BRONZE_DIR / batch_id

    if not bronze_batch.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {bronze_batch}"
        )

    # Validate ingestion manifest
    ingestion_manifest_path = (
        bronze_batch / "ingestion_manifest.json"
    )

    if not ingestion_manifest_path.exists():
        raise FileNotFoundError(
            f"Ingestion manifest not found: {ingestion_manifest_path}"
        )

    with open(
        ingestion_manifest_path,
        "r",
        encoding="utf-8"
    ) as file:

        ingestion_manifest = json.load(file)

    if ingestion_manifest.get("batch_id") != batch_id:
        raise ValueError(
            "Ingestion manifest batch_id does not match requested batch_id."
        )

    source_path = bronze_batch / "goods_receipts.csv"

    po_lines_path = (
        SILVER_DIR
        / batch_id
        / "purchase_order_lines.csv"
    )

    purchase_orders_path = (
        SILVER_DIR
        / batch_id
        / "purchase_orders.csv"
    )

    if not source_path.exists():
        raise FileNotFoundError(
            f"Bronze goods_receipts not found: {source_path}"
        )

    if not po_lines_path.exists():
        raise FileNotFoundError(
            "Silver purchase_order_lines not found."
        )

    if not purchase_orders_path.exists():
        raise FileNotFoundError(
            "Silver purchase_orders not found."
        )

    # Load source and reference data
    df = pd.read_csv(source_path)

    po_lines = pd.read_csv(po_lines_path)

    purchase_orders = pd.read_csv(
        purchase_orders_path
    )

    input_count = len(df)

    print(f"\nSource Batch: {batch_id}")
    print(f"Input Records: {input_count}")

    # =====================================================
    # 1. SCHEMA VALIDATION
    # =====================================================

    required_columns = [
        "receipt_id",
        "po_line_id",
        "received_date",
        "received_qty",
        "accepted_qty",
        "rejected_qty",
    ]

    missing_columns = (
        set(required_columns) - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    required_po_line_columns = [
        "po_line_id",
        "po_id",
        "ordered_qty",
    ]

    missing_po_line_columns = (
        set(required_po_line_columns) - set(po_lines.columns)
    )

    if missing_po_line_columns:
        raise ValueError(
            "Missing purchase_order_lines columns: "
            f"{missing_po_line_columns}"
        )

    required_po_columns = [
        "po_id",
        "order_date",
        "expected_delivery_date",
    ]

    missing_po_columns = (
        set(required_po_columns) - set(purchase_orders.columns)
    )

    if missing_po_columns:
        raise ValueError(
            "Missing purchase_orders columns: "
            f"{missing_po_columns}"
        )

    # =====================================================
    # 2. DATA STANDARDIZATION
    # =====================================================

    for column in [
        "receipt_id",
        "po_line_id",
    ]:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    df["received_date"] = pd.to_datetime(
        df["received_date"],
        errors="coerce"
    )

    numeric_columns = [
        "received_qty",
        "accepted_qty",
        "rejected_qty",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # =====================================================
    # 3. DATA QUALITY RULES
    # =====================================================

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
                f"{current}; {reason}"
                if current
                else reason
            )
        )

    # Required fields
    for column in required_columns:

        reject(
            df[column].isna(),
            f"Missing or invalid {column}"
        )

    # Primary Key
    reject(
        df["receipt_id"].duplicated(keep=False),
        "Duplicate receipt_id"
    )

    # Foreign Key
    valid_po_line_ids = set(
        po_lines["po_line_id"]
    )

    reject(
        ~df["po_line_id"].isin(valid_po_line_ids),
        "Invalid po_line_id"
    )

    # Quantity validations
    reject(
        df["received_qty"].notna()
        & (df["received_qty"] <= 0),
        "Invalid received_qty"
    )

    for column in [
        "accepted_qty",
        "rejected_qty",
    ]:

        reject(
            df[column].notna()
            & (df[column] < 0),
            f"Negative {column}"
        )

    # Quantity reconciliation
    reject(
        df["received_qty"].notna()
        & df["accepted_qty"].notna()
        & df["rejected_qty"].notna()
        & (
            df["received_qty"]
            != (
                df["accepted_qty"]
                + df["rejected_qty"]
            )
        ),
        "Received quantity reconciliation failed"
    )

    # Date validation
    reject(
        df["received_date"].isna(),
        "Invalid received_date"
    )

    # =====================================================
    # 4. DATA ENRICHMENT
    # =====================================================

    po_dates = po_lines[
        [
            "po_line_id",
            "po_id",
        ]
    ].merge(
        purchase_orders[
            [
                "po_id",
                "order_date",
                "expected_delivery_date",
            ]
        ],
        on="po_id",
        how="left",
        validate="many_to_one"
    )

    po_dates["order_date"] = pd.to_datetime(
        po_dates["order_date"],
        errors="coerce"
    )

    po_dates["expected_delivery_date"] = (
        pd.to_datetime(
            po_dates["expected_delivery_date"],
            errors="coerce"
        )
    )

    df = df.merge(
        po_dates,
        on="po_line_id",
        how="left",
        validate="many_to_one"
    )

    # Receipt must not precede order date
    reject(
        df["received_date"].notna()
        & df["order_date"].notna()
        & (
            df["received_date"]
            < df["order_date"]
        ),
        "Receipt date before order date"
    )

    # =====================================================
    # 5. SPLIT VALID AND QUARANTINED RECORDS
    # =====================================================

    df["rejection_reason"] = rejection_reasons

    valid_df = df[
        rejection_reasons.eq("")
    ].copy()

    quarantine_df = df[
        rejection_reasons.ne("")
    ].copy()

    print("\nData Quality Results:")
    print(f"Valid Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")

    # =====================================================
    # 6. BUSINESS TRANSFORMATIONS
    # =====================================================

    valid_df["days_from_order"] = (
        valid_df["received_date"]
        - valid_df["order_date"]
    ).dt.days

    valid_df["days_after_expected"] = (
        valid_df["received_date"]
        - valid_df["expected_delivery_date"]
    ).dt.days

    valid_df["is_late_receipt"] = (
        valid_df["days_after_expected"] > 0
    )

    valid_df["is_fully_accepted"] = (
        valid_df["accepted_qty"]
        == valid_df["received_qty"]
    )

    valid_df["acceptance_rate"] = (
        valid_df["accepted_qty"]
        / valid_df["received_qty"]
    ).round(4)

    # =====================================================
    # 7. QUANTITY VALIDATION PER PO LINE
    # =====================================================

    received_totals = (
        valid_df
        .groupby(
            "po_line_id",
            as_index=False
        )["received_qty"]
        .sum()
        .rename(
            columns={
                "received_qty": "total_received_qty"
            }
        )
    )

    quantity_comparison = received_totals.merge(
        po_lines[
            [
                "po_line_id",
                "ordered_qty",
            ]
        ],
        on="po_line_id",
        how="left",
        validate="one_to_one"
    )

    quantity_comparison[
        "exceeds_ordered_qty"
    ] = (
        quantity_comparison["total_received_qty"]
        > quantity_comparison["ordered_qty"]
    )

    exceeded = quantity_comparison[
        quantity_comparison["exceeds_ordered_qty"]
    ]

    assert exceeded.empty, (
        "Received quantity exceeds ordered quantity:\n"
        f"{exceeded.to_string(index=False)}"
    )

    # =====================================================
    # 8. SILVER VALIDATION
    # =====================================================

    assert (
        len(valid_df) + len(quarantine_df)
        == input_count
    )

    assert valid_df["receipt_id"].is_unique

    assert (
        valid_df[required_columns]
        .notna()
        .all()
        .all()
    )

    assert valid_df["po_line_id"].isin(
        valid_po_line_ids
    ).all()

    assert (
        valid_df["received_qty"]
        == (
            valid_df["accepted_qty"]
            + valid_df["rejected_qty"]
        )
    ).all()

    assert (
        valid_df["received_date"]
        >= valid_df["order_date"]
    ).all()

    assert valid_df[
        "acceptance_rate"
    ].between(0, 1).all()

    print("\nAll Silver validation checks passed.")

    # =====================================================
    # 9. SAVE SILVER OUTPUTS
    # =====================================================

    output_dir = SILVER_DIR / batch_id

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    valid_df.to_csv(
        output_dir / "goods_receipts.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    quarantine_df.to_csv(
        output_dir / "goods_receipts_quarantine.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    # =====================================================
    # 10. TRANSFORMATION MANIFEST
    # =====================================================

    manifest = {
        "dataset": "goods_receipts",
        "source_batch_id": batch_id,
        "batch_id": batch_id,
        "transformation_timestamp": (
            datetime.now(timezone.utc).isoformat()
        ),
        "input_records": input_count,
        "silver_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "late_receipts": int(
            valid_df["is_late_receipt"].sum()
        ),
        "status": "SUCCESS",
    }

    with open(
        output_dir
        / "goods_receipts_transformation_manifest.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            manifest,
            file,
            indent=4
        )

    # =====================================================
    # 11. SUMMARY
    # =====================================================

    print("\n" + "=" * 55)
    print("TRANSFORMATION SUMMARY")
    print("=" * 55)

    print(f"Batch ID: {batch_id}")
    print(f"Input Records: {input_count}")
    print(f"Silver Records: {len(valid_df)}")
    print(f"Quarantined Records: {len(quarantine_df)}")

    print(
        "Late Receipts:",
        int(valid_df["is_late_receipt"].sum())
    )

    print(
        "Average Acceptance Rate:",
        round(
            valid_df["acceptance_rate"].mean() * 100,
            2
        ),
        "%"
    )

    print(
        "Total Accepted Quantity:",
        int(valid_df["accepted_qty"].sum())
    )

    print(
        "Total Rejected Quantity:",
        int(valid_df["rejected_qty"].sum())
    )

    print("\nTransformation completed successfully!")

    return {
        "batch_id": batch_id,
        "input_records": input_count,
        "valid_records": len(valid_df),
        "quarantined_records": len(quarantine_df),
        "late_receipts": int(
            valid_df["is_late_receipt"].sum()
        ),
        "status": "SUCCESS",
    }


# =========================================================
# SCRIPT ENTRY POINT
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Transform goods receipts from Bronze to Silver."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Bronze ingestion batch ID to process."
    )

    args = parser.parse_args()

    main(args.batch_id)
