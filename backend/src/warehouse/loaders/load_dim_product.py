
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "products.csv"
)

# Initial historical baseline assumption
BASELINE_DATE = date(2025, 1, 1)

REQUIRED_COLUMNS = {
    "product_id",
    "product_name",
    "category",
    "brand",
    "standard_cost",
    "current_selling_price",
    "reorder_level",
    "is_active",
}


INSERT_PRODUCT_SQL = text("""
    INSERT INTO gold.dim_product (
        product_id,
        product_name,
        category,
        brand,
        standard_cost,
        current_selling_price,
        reorder_level,
        is_active,
        valid_from,
        valid_to,
        is_current
    )
    VALUES (
        :product_id,
        :product_name,
        :category,
        :brand,
        :standard_cost,
        :current_selling_price,
        :reorder_level,
        :is_active,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    )
    ON CONFLICT (product_id) WHERE is_current = TRUE
    DO NOTHING
""")


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_products():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Silver source file not found: {SOURCE_FILE}"
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

        products = list(reader)

    if not products:
        raise ValueError("Source file contains no products.")

    product_ids = [row["product_id"] for row in products]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError("Duplicate product_id found in source.")

    records = []

    for row in products:
        standard_cost = Decimal(row["standard_cost"])
        selling_price = Decimal(row["current_selling_price"])
        reorder_level = int(row["reorder_level"])

        if standard_cost < 0 or selling_price < 0:
            raise ValueError(
                f"Negative price or cost for {row['product_id']}"
            )

        if reorder_level < 0:
            raise ValueError(
                f"Negative reorder level for {row['product_id']}"
            )

        records.append({
            "product_id": row["product_id"].strip(),
            "product_name": row["product_name"].strip(),
            "category": row["category"].strip(),
            "brand": row["brand"].strip(),
            "standard_cost": standard_cost,
            "current_selling_price": selling_price,
            "reorder_level": reorder_level,
            "is_active": parse_boolean(row["is_active"]),
            "valid_from": BASELINE_DATE,
        })

    return records


def main():
    print("Starting Product Dimension Initial Load...")

    products = read_products()

    print(f"Source records validated: {len(products)}")

    engine = get_database_engine()

    with engine.begin() as connection:
        result = connection.execute(
            INSERT_PRODUCT_SQL,
            products
        )

        inserted_count = result.rowcount

    skipped_count = len(products) - inserted_count

    print("\nProduct Dimension Load Summary")
    print("--------------------------------")
    print(f"Source records:   {len(products)}")
    print(f"Inserted records: {inserted_count}")
    print(f"Skipped records:  {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
