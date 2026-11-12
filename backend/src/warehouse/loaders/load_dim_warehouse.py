
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "warehouses.csv"
)

BASELINE_DATE = date(2025, 1, 1)

REQUIRED_COLUMNS = {
    "warehouse_id",
    "warehouse_name",
    "city",
    "region",
    "capacity_units",
    "is_active",
}


INSERT_WAREHOUSE_SQL = text("""
    INSERT INTO gold.dim_warehouse (
        warehouse_id,
        warehouse_name,
        city,
        region,
        capacity_units,
        is_active,
        valid_from,
        valid_to,
        is_current
    )
    VALUES (
        :warehouse_id,
        :warehouse_name,
        :city,
        :region,
        :capacity_units,
        :is_active,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    )
    ON CONFLICT (warehouse_id) WHERE is_current = TRUE
    DO NOTHING
""")


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_warehouses():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    with SOURCE_FILE.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        source_columns = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - source_columns

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        warehouses = list(reader)

    if not warehouses:
        raise ValueError("Source file contains no warehouses.")

    warehouse_ids = [
        row["warehouse_id"].strip()
        for row in warehouses
    ]

    if len(warehouse_ids) != len(set(warehouse_ids)):
        raise ValueError("Duplicate warehouse_id found in source.")

    records = []

    for row in warehouses:
        warehouse_id = row["warehouse_id"].strip()

        required_values = [
            warehouse_id,
            row["warehouse_name"],
            row["city"],
            row["region"],
        ]

        if any(
            not value or not value.strip()
            for value in required_values
        ):
            raise ValueError(
                f"Missing required value for warehouse {warehouse_id}"
            )

        capacity_units = int(row["capacity_units"])

        if capacity_units <= 0:
            raise ValueError(
                f"Invalid capacity for warehouse {warehouse_id}"
            )

        records.append({
            "warehouse_id": warehouse_id,
            "warehouse_name": row["warehouse_name"].strip(),
            "city": row["city"].strip(),
            "region": row["region"].strip(),
            "capacity_units": capacity_units,
            "is_active": parse_boolean(row["is_active"]),
            "valid_from": BASELINE_DATE,
        })

    return records


def main():
    print("Starting Warehouse Dimension Initial Load...")

    warehouses = read_warehouses()

    print(f"Source records validated: {len(warehouses)}")

    engine = get_database_engine()

    with engine.begin() as connection:
        result = connection.execute(
            INSERT_WAREHOUSE_SQL,
            warehouses
        )

        inserted_count = result.rowcount

    skipped_count = len(warehouses) - inserted_count

    print("\nWarehouse Dimension Load Summary")
    print("--------------------------------")
    print(f"Source records:   {len(warehouses)}")
    print(f"Inserted records: {inserted_count}")
    print(f"Skipped records:  {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
