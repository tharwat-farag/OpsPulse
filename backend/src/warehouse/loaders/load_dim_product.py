
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Initial historical baseline assumption.
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


# =========================================================
# 1. PARSE BOOLEAN
# =========================================================

def parse_boolean(value: str) -> bool:

    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"Invalid boolean value: {value}"
    )


# =========================================================
# 2. READ AND VALIDATE PRODUCTS
# =========================================================

def read_products(batch_id: str) -> list[dict]:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "products.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Silver source file not found: {source_file}"
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

        products = list(reader)

    if not products:
        raise ValueError(
            "Source file contains no products."
        )

    records = []
    product_ids = set()

    for row in products:

        product_id = row["product_id"].strip()

        if not product_id:
            raise ValueError(
                "Empty product_id found."
            )

        if product_id in product_ids:
            raise ValueError(
                f"Duplicate product_id found: {product_id}"
            )

        product_ids.add(product_id)

        product_name = row["product_name"].strip()
        category = row["category"].strip()
        brand = row["brand"].strip()

        if not product_name or not category or not brand:
            raise ValueError(
                f"Missing product attributes for {product_id}."
            )

        try:
            standard_cost = Decimal(
                row["standard_cost"]
            )

            selling_price = Decimal(
                row["current_selling_price"]
            )

            reorder_level = int(
                row["reorder_level"]
            )

        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"Invalid numeric values for product {product_id}."
            ) from exc

        if not standard_cost.is_finite():
            raise ValueError(
                f"Invalid standard_cost for {product_id}."
            )

        if not selling_price.is_finite():
            raise ValueError(
                f"Invalid selling price for {product_id}."
            )

        if standard_cost < 0 or selling_price < 0:
            raise ValueError(
                f"Negative price or cost for {product_id}."
            )

        if reorder_level < 0:
            raise ValueError(
                f"Negative reorder level for {product_id}."
            )

        records.append({
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "brand": brand,
            "standard_cost": standard_cost,
            "current_selling_price": selling_price,
            "reorder_level": reorder_level,
            "is_active": parse_boolean(row["is_active"]),
            "valid_from": BASELINE_DATE,
        })

    print(f"Source records validated: {len(records):,}")
    print("Product source validation: PASSED")

    return records


# =========================================================
# 3. LOAD PRODUCT DIMENSION
# =========================================================

def load_products(products: list[dict]) -> None:

    print("\nLoading Product Dimension...")

    engine = get_database_engine()

    try:

        with engine.begin() as connection:

            result = connection.execute(
                INSERT_PRODUCT_SQL,
                products,
            )

            inserted_count = result.rowcount

        skipped_count = len(products) - inserted_count

        print("\nProduct Dimension Load Summary")
        print("--------------------------------")
        print(f"Source records:   {len(products):,}")
        print(f"Inserted records: {inserted_count:,}")
        print(f"Skipped records:  {skipped_count:,}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


# =========================================================
# 4. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError(
            "A valid batch_id is required."
        )

    print("=" * 55)
    print("OPSPULSE - PRODUCT DIMENSION INITIAL LOAD")
    print(f"Batch ID: {batch_id}")
    print("=" * 55)

    products = read_products(batch_id)

    load_products(products)

    print("\nProduct Dimension Initial Load completed.")


# =========================================================
# 5. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Product Dimension baseline data."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
