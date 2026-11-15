
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]

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


def read_warehouses(batch_id: str) -> list[dict]:
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must not be empty.")

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "warehouses.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    with source_file.open(
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

        try:
            capacity_units = int(row["capacity_units"].strip())
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid capacity for warehouse {warehouse_id}: "
                f"{row['capacity_units']}"
            ) from exc

        if capacity_units <= 0:
            raise ValueError(
                f"Capacity must be positive for warehouse {warehouse_id}"
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


def main(batch_id: str) -> None:
    print("Starting Warehouse Dimension Initial Load...")
    print(f"Batch ID: {batch_id}")

    warehouses = read_warehouses(batch_id)

    print(f"Source records validated: {len(warehouses)}")

    engine = get_database_engine()

    try:
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

    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Load Warehouse Dimension from a Silver batch."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Silver batch ID to load."
    )

    args = parser.parse_args()
    main(args.batch_id)
