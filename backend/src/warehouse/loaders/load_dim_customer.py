
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
    / "customers.csv"
)

BASELINE_DATE = date(2025, 1, 1)

REQUIRED_COLUMNS = {
    "customer_id",
    "customer_name",
    "customer_type",
    "city",
    "registration_date",
}


INSERT_CUSTOMER_SQL = text("""
    INSERT INTO gold.dim_customer (
        customer_id,
        customer_name,
        customer_type,
        city,
        registration_date,
        valid_from,
        valid_to,
        is_current
    )
    VALUES (
        :customer_id,
        :customer_name,
        :customer_type,
        :city,
        :registration_date,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    )
    ON CONFLICT (customer_id) WHERE is_current = TRUE
    DO NOTHING
""")


def read_customers():
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

        customers = list(reader)

    if not customers:
        raise ValueError("Source file contains no customers.")

    customer_ids = [
        row["customer_id"].strip()
        for row in customers
    ]

    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError("Duplicate customer_id found in source.")

    records = []

    for row in customers:
        customer_type = row["customer_type"].strip()

        if customer_type not in {"Business", "Individual"}:
            raise ValueError(
                f"Invalid customer type for {row['customer_id']}"
            )

        records.append({
            "customer_id": row["customer_id"].strip(),
            "customer_name": row["customer_name"].strip(),
            "customer_type": customer_type,
            "city": row["city"].strip(),
            "registration_date": date.fromisoformat(
                row["registration_date"].strip()
            ),
            "valid_from": BASELINE_DATE,
        })

    return records


def main():
    print("Starting Customer Dimension Initial Load...")

    customers = read_customers()

    print(f"Source records validated: {len(customers)}")

    engine = get_database_engine()

    with engine.begin() as connection:
        result = connection.execute(
            INSERT_CUSTOMER_SQL,
            customers
        )

        inserted_count = result.rowcount

    skipped_count = len(customers) - inserted_count

    print("\nCustomer Dimension Load Summary")
    print("--------------------------------")
    print(f"Source records:   {len(customers)}")
    print(f"Inserted records: {inserted_count}")
    print(f"Skipped records:  {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
