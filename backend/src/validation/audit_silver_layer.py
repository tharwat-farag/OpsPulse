
import argparse
import json
from pathlib import Path

import pandas as pd


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SILVER_DIR = PROJECT_ROOT / "data" / "silver"

DATASETS = [
    "products",
    "customers",
    "branches",
    "suppliers",
    "warehouses",
    "product_suppliers",
    "sales",
    "inventory",
    "purchase_orders",
    "purchase_order_lines",
    "goods_receipts",
    "operating_expenses",
]


# ==========================================
# 2. AUDIT SINGLE DATASET
# ==========================================

def audit_dataset(dataset, silver_batch_dir, batch_id):

    silver_file = silver_batch_dir / f"{dataset}.csv"

    quarantine_file = (
        silver_batch_dir / f"{dataset}_quarantine.csv"
    )

    manifest_file = (
        silver_batch_dir
        / f"{dataset}_transformation_manifest.json"
    )

    missing = []

    if not silver_file.exists():
        missing.append("Silver file")

    if not quarantine_file.exists():
        missing.append("Quarantine file")

    if not manifest_file.exists():
        missing.append("Transformation manifest")

    if missing:
        return {
            "Dataset": dataset,
            "Silver Rows": 0,
            "Quarantine Rows": 0,
            "Status": "MISSING: " + ", ".join(missing),
        }

    try:
        silver_df = pd.read_csv(silver_file)

        quarantine_df = pd.read_csv(quarantine_file)

        with open(
            manifest_file,
            "r",
            encoding="utf-8"
        ) as file:
            manifest = json.load(file)

    except Exception as exc:

        return {
            "Dataset": dataset,
            "Silver Rows": 0,
            "Quarantine Rows": 0,
            "Status": f"READ ERROR: {exc}",
        }

    errors = []

    # Validate batch identity when declared in the manifest
    manifest_batch = manifest.get(
        "batch_id",
        manifest.get("source_batch")
    )

    if (
        manifest_batch is not None
        and manifest_batch != batch_id
    ):
        errors.append("Batch ID mismatch")

    # Validate dataset identity when declared
    manifest_dataset = manifest.get("dataset")

    if (
        manifest_dataset is not None
        and manifest_dataset != dataset
    ):
        errors.append("Dataset name mismatch")

    # Support the existing manifest naming conventions
    expected_silver_rows = manifest.get(
        "valid_records",
        manifest.get("silver_records")
    )

    expected_quarantine_rows = manifest.get(
        "quarantined_records"
    )

    if (
        expected_silver_rows is not None
        and len(silver_df) != expected_silver_rows
    ):
        errors.append("Silver row count mismatch")

    if (
        expected_quarantine_rows is not None
        and len(quarantine_df) != expected_quarantine_rows
    ):
        errors.append("Quarantine row count mismatch")

    # Reconcile input records when the manifest provides the count
    expected_input_rows = manifest.get("input_records")

    if expected_input_rows is not None:

        actual_input_rows = (
            len(silver_df) + len(quarantine_df)
        )

        if actual_input_rows != expected_input_rows:
            errors.append("Input reconciliation failed")

    # Check transformation status when declared
    manifest_status = manifest.get("status")

    if (
        manifest_status is not None
        and manifest_status != "SUCCESS"
    ):
        errors.append(
            f"Transformation status: {manifest_status}"
        )

    status = (
        "OK"
        if not errors
        else "FAILED: " + "; ".join(errors)
    )

    return {
        "Dataset": dataset,
        "Silver Rows": len(silver_df),
        "Quarantine Rows": len(quarantine_df),
        "Status": status,
    }


# ==========================================
# 3. MAIN SILVER AUDIT
# ==========================================

def main(batch_id: str) -> dict:

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must be provided.")

    batch_id = batch_id.strip()

    if Path(batch_id).name != batch_id:
        raise ValueError("Invalid batch_id.")

    silver_batch_dir = SILVER_DIR / batch_id

    if not silver_batch_dir.is_dir():
        raise FileNotFoundError(
            f"Silver batch directory not found: {silver_batch_dir}"
        )

    print("=" * 75)
    print("OPSPULSE - SILVER LAYER FINAL AUDIT")
    print("=" * 75)

    print(f"Batch: {batch_id}\n")

    results = []

    # Audit all expected datasets
    for dataset in DATASETS:

        result = audit_dataset(
            dataset,
            silver_batch_dir,
            batch_id
        )

        results.append(result)

    audit_df = pd.DataFrame(results)

    print(audit_df.to_string(index=False))

    print("\n" + "=" * 75)

    all_passed = (
        audit_df["Status"] == "OK"
    ).all()

    total_silver = int(
        audit_df["Silver Rows"].sum()
    )

    total_quarantine = int(
        audit_df["Quarantine Rows"].sum()
    )

    failed_datasets = audit_df.loc[
        audit_df["Status"] != "OK",
        "Dataset"
    ].tolist()

    print(f"Total Silver Records: {total_silver:,}")
    print(f"Total Quarantine Records: {total_quarantine:,}")
    print(f"Datasets Audited: {len(DATASETS)}")
    print(f"All Required Checks Passed: {all_passed}")

    if not all_passed:

        print("\nSILVER LAYER AUDIT FAILED!")

        raise RuntimeError(
            "Silver audit failed for datasets: "
            + ", ".join(failed_datasets)
        )

    print("\nSILVER LAYER AUDIT PASSED!")

    return {
        "batch_id": batch_id,
        "datasets_audited": len(DATASETS),
        "total_silver_records": total_silver,
        "total_quarantine_records": total_quarantine,
        "status": "SUCCESS",
    }


# ==========================================
# 4. SCRIPT ENTRY POINT
# ==========================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Audit the OpsPulse Silver layer."
    )

    parser.add_argument(
        "batch_id",
        help="The exact Silver batch ID to audit."
    )

    args = parser.parse_args()

    main(args.batch_id)
