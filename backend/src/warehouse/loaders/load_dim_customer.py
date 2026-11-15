
import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

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


# =========================================================
# 1. READ AND VALIDATE CUSTOMERS
# =========================================================

def read_customers(batch_id: str) -> list[dict]:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "customers.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    with source_file.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        source_columns = set(reader.fieldnames or [])

        missing_columns = (
            REQUIRED_COLUMNS - source_columns
        )

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        customers = list(reader)

    if not customers:
        raise ValueError(
            "Source file contains no customers."
        )

    records = []
    customer_ids = set()

    for row in customers:

        customer_id = row["customer_id"].strip()

        if not customer_id:
            raise ValueError(
                "Empty customer_id found."
            )

        if customer_id in customer_ids:
            raise ValueError(
                f"Duplicate customer_id found: {customer_id}"
            )

        customer_ids.add(customer_id)

        customer_name = row["customer_name"].strip()
        customer_type = row["customer_type"].strip()
        city = row["city"].strip()

        if not customer_name or not city:
            raise ValueError(
                f"Missing customer name or city for {customer_id}."
            )

        if customer_type not in {"Business", "Individual"}:
            raise ValueError(
                f"Invalid customer type for {customer_id}: "
                f"{customer_type}"
            )

        try:
            registration_date = date.fromisoformat(
                row["registration_date"].strip()
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid registration_date for {customer_id}."
            ) from exc

        records.append({
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_type": customer_type,
            "city": city,
            "registration_date": registration_date,
            "valid_from": BASELINE_DATE,
        })

    print(f"Source records validated: {len(records):,}")
    print("Customer source validation: PASSED")

    return records


# =========================================================
# 2. LOAD CUSTOMER DIMENSION
# =========================================================

def load_customers(customers: list[dict]) -> None:

    print("\nLoading Customer Dimension...")

    engine = get_database_engine()

    try:

        with engine.begin() as connection:

            result = connection.execute(
                INSERT_CUSTOMER_SQL,
                customers,
            )

            inserted_count = result.rowcount

        skipped_count = len(customers) - inserted_count

        print("\nCustomer Dimension Load Summary")
        print("--------------------------------")
        print(f"Source records:   {len(customers):,}")
        print(f"Inserted records: {inserted_count:,}")
        print(f"Skipped records:  {skipped_count:,}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


# =========================================================
# 3. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError(
            "A valid batch_id is required."
        )

    print("=" * 55)
    print("OPSPULSE - CUSTOMER DIMENSION INITIAL LOAD")
    print(f"Batch ID: {batch_id}")
    print("=" * 55)

    customers = read_customers(batch_id)

    load_customers(customers)

    print("\nCustomer Dimension Initial Load completed.")


# =========================================================
# 4. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Customer Dimension baseline data."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
