
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]

BASELINE_DATE = date(2025, 1, 1)

REQUIRED_COLUMNS = {
    "supplier_id",
    "supplier_name",
    "city",
    "contact_email",
    "rating",
    "is_active",
}


INSERT_SUPPLIER_SQL = text("""
    INSERT INTO gold.dim_supplier (
        supplier_id,
        supplier_name,
        city,
        contact_email,
        rating,
        is_active,
        valid_from,
        valid_to,
        is_current
    )
    VALUES (
        :supplier_id,
        :supplier_name,
        :city,
        :contact_email,
        :rating,
        :is_active,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    )
    ON CONFLICT (supplier_id) WHERE is_current = TRUE
    DO NOTHING
""")


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_suppliers(batch_id: str) -> list[dict]:
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must not be empty.")

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "suppliers.csv"
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

        suppliers = list(reader)

    if not suppliers:
        raise ValueError("Source file contains no suppliers.")

    supplier_ids = [
        row["supplier_id"].strip()
        for row in suppliers
    ]

    if len(supplier_ids) != len(set(supplier_ids)):
        raise ValueError("Duplicate supplier_id found in source.")

    records = []

    for row in suppliers:
        supplier_id = row["supplier_id"].strip()

        required_values = [
            supplier_id,
            row["supplier_name"],
            row["city"],
            row["contact_email"],
        ]

        if any(
            not value or not value.strip()
            for value in required_values
        ):
            raise ValueError(
                f"Missing required value for supplier {supplier_id}"
            )

        try:
            rating = Decimal(row["rating"].strip())
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid rating for supplier {supplier_id}"
            ) from exc

        if (
            not rating.is_finite()
            or not Decimal("0") <= rating <= Decimal("5")
        ):
            raise ValueError(
                f"Rating out of range for supplier {supplier_id}: {rating}"
            )

        records.append({
            "supplier_id": supplier_id,
            "supplier_name": row["supplier_name"].strip(),
            "city": row["city"].strip(),
            "contact_email": row["contact_email"].strip(),
            "rating": rating,
            "is_active": parse_boolean(row["is_active"]),
            "valid_from": BASELINE_DATE,
        })

    return records


def main(batch_id: str) -> None:
    print("Starting Supplier Dimension Initial Load...")
    print(f"Batch ID: {batch_id}")

    suppliers = read_suppliers(batch_id)

    print(f"Source records validated: {len(suppliers)}")

    engine = get_database_engine()

    try:
        with engine.begin() as connection:
            result = connection.execute(
                INSERT_SUPPLIER_SQL,
                suppliers
            )

            inserted_count = result.rowcount

        skipped_count = len(suppliers) - inserted_count

        print("\nSupplier Dimension Load Summary")
        print("--------------------------------")
        print(f"Source records:   {len(suppliers)}")
        print(f"Inserted records: {inserted_count}")
        print(f"Skipped records:  {skipped_count}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Load Supplier Dimension from a Silver batch."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Silver batch ID to load."
    )

    args = parser.parse_args()
    main(args.batch_id)
