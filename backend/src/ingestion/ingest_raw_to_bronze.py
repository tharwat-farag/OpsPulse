
import hashlib
import json
import shutil
import sys
import uuid

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ==================================================
# 1. PROJECT PATHS AND CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONFIG_DIR = (
    PROJECT_ROOT
    / "backend"
    / "src"
    / "data_generation"
)

# Allow Python to find config.py
sys.path.insert(0, str(CONFIG_DIR))

from config import RAW_DATA_DIR


BRONZE_DATA_DIR = PROJECT_ROOT / "data" / "bronze"


# ==================================================
# 2. EXPECTED SOURCE FILES
# ==================================================

EXPECTED_FILES = [
    "branches.csv",
    "warehouses.csv",
    "products.csv",
    "customers.csv",
    "suppliers.csv",
    "product_suppliers.csv",
    "sales.csv",
    "purchase_orders.csv",
    "purchase_order_lines.csv",
    "goods_receipts.csv",
    "inventory.csv",
    "operating_expenses.csv",
]


# ==================================================
# 3. CHECKSUM FUNCTION
# ==================================================

def calculate_checksum(file_path):
    """
    Calculate SHA-256 checksum for a file.
    Used to verify that the copied file
    has exactly the same content as the source.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ==================================================
# 4. VALIDATE SOURCE FILES
# ==================================================

def validate_source_files():

    print("\nChecking source files...")

    missing_files = [
        file_name
        for file_name in EXPECTED_FILES
        if not (RAW_DATA_DIR / file_name).exists()
    ]

    if missing_files:

        raise FileNotFoundError(
            f"Missing source files: {missing_files}"
        )

    print(
        f"All {len(EXPECTED_FILES)} source files found."
    )


# ==================================================
# 5. INGEST ONE FILE
# ==================================================

def ingest_file(file_name, batch_dir):

    source_path = RAW_DATA_DIR / file_name

    destination_path = batch_dir / file_name

    # Read the CSV to count its records.
    dataframe = pd.read_csv(source_path)

    row_count = len(dataframe)

    if row_count == 0:

        raise ValueError(
            f"Source file is empty: {file_name}"
        )

    # Copy the source file without modifying its contents.
    shutil.copy2(
        source_path,
        destination_path,
    )

    # Verify source and destination integrity.
    source_checksum = calculate_checksum(
        source_path
    )

    bronze_checksum = calculate_checksum(
        destination_path
    )

    if source_checksum != bronze_checksum:

        raise ValueError(
            f"Checksum mismatch: {file_name}"
        )

    return {
        "file_name": file_name,
        "row_count": row_count,
        "file_size_bytes": destination_path.stat().st_size,
        "sha256": bronze_checksum,
        "status": "SUCCESS",
    }


# ==================================================
# 6. MAIN INGESTION PIPELINE
# ==================================================

def main():

    print("=" * 55)
    print("       RAW TO BRONZE INGESTION PIPELINE")
    print("=" * 55)

    # Step 1: Validate source files.
    validate_source_files()

    # Step 2: Generate a unique batch ID.
    timestamp = datetime.now(timezone.utc)

    batch_id = (
        "batch_"
        + timestamp.strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    # Step 3: Create a new Bronze batch directory.
    batch_dir = BRONZE_DATA_DIR / batch_id

    batch_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    print(f"\nBatch ID: {batch_id}")

    print("\nStarting file ingestion...")

    ingestion_results = []

    # Step 4: Ingest all expected files.
    for file_name in EXPECTED_FILES:

        print(f"\nIngesting: {file_name}")

        result = ingest_file(
            file_name,
            batch_dir,
        )

        ingestion_results.append(result)

        print(
            f"SUCCESS | "
            f"Records: {result['row_count']:,} | "
            f"Size: {result['file_size_bytes']:,} bytes"
        )

    # Step 5: Calculate total records.
    total_records = sum(
        item["row_count"]
        for item in ingestion_results
    )

    # Step 6: Build ingestion manifest.
    manifest = {
        "batch_id": batch_id,

        "ingestion_timestamp_utc": (
            timestamp.isoformat()
        ),

        "source_directory": "data/raw",

        "destination_directory": str(
            batch_dir.relative_to(PROJECT_ROOT)
        ),

        "total_files": len(ingestion_results),

        "total_records": total_records,

        "status": "SUCCESS",

        "files": ingestion_results,
    }

    # Step 7: Save manifest.
    manifest_path = (
        batch_dir / "ingestion_manifest.json"
    )

    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            indent=4,
            ensure_ascii=False,
        )

    # Step 8: Print final summary.
    print("\n" + "=" * 55)
    print("             INGESTION SUMMARY")
    print("=" * 55)

    print(f"Batch ID: {batch_id}")

    print(
        f"Files Ingested: "
        f"{len(ingestion_results)}"
    )

    print(
        f"Total Records: "
        f"{total_records:,}"
    )

    print(
        f"Manifest: {manifest_path}"
    )

    print("\nRAW TO BRONZE INGESTION COMPLETED!")

    # Return batch_id for Airflow XCom.
    return batch_id


# ==================================================
# 7. SCRIPT ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()
