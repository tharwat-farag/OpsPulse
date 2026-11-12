
import csv
from decimal import Decimal, InvalidOperation
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
    / "product_suppliers.csv"
)

REQUIRED_COLUMNS = {
    "product_id",
    "supplier_id",
    "supplier_price",
    "lead_time_days",
    "minimum_order_qty",
    "is_preferred_supplier",
}


INSERT_BRIDGE_SQL = text("""
    INSERT INTO gold.bridge_product_supplier (
        product_key,
        supplier_key,
        supplier_price,
        lead_time_days,
        minimum_order_qty,
        is_preferred_supplier
    )
    SELECT
        product.product_key,
        supplier.supplier_key,
        :supplier_price,
        :lead_time_days,
        :minimum_order_qty,
        :is_preferred_supplier
    FROM gold.dim_product AS product
    CROSS JOIN gold.dim_supplier AS supplier
    WHERE product.product_id = :product_id
      AND product.is_current = TRUE
      AND supplier.supplier_id = :supplier_id
      AND supplier.is_current = TRUE
    ON CONFLICT (product_key, supplier_key)
    DO NOTHING
""")


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_relationships():
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

        relationships = list(reader)

    if not relationships:
        raise ValueError("Source file contains no relationships.")

    pairs = [
        (
            row["product_id"].strip(),
            row["supplier_id"].strip()
        )
        for row in relationships
    ]

    if len(pairs) != len(set(pairs)):
        raise ValueError("Duplicate product-supplier pair found.")

    records = []

    for row in relationships:
        product_id = row["product_id"].strip()
        supplier_id = row["supplier_id"].strip()

        try:
            supplier_price = Decimal(row["supplier_price"].strip())
            lead_time_days = int(row["lead_time_days"])
            minimum_order_qty = int(row["minimum_order_qty"])
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"Invalid numeric values for {product_id}/{supplier_id}"
            ) from exc

        if not supplier_price.is_finite() or supplier_price < 0:
            raise ValueError(
                f"Invalid supplier price for {product_id}/{supplier_id}"
            )

        if lead_time_days < 0 or minimum_order_qty <= 0:
            raise ValueError(
                f"Invalid lead time or minimum quantity for "
                f"{product_id}/{supplier_id}"
            )

        records.append({
            "product_id": product_id,
            "supplier_id": supplier_id,
            "supplier_price": supplier_price,
            "lead_time_days": lead_time_days,
            "minimum_order_qty": minimum_order_qty,
            "is_preferred_supplier": parse_boolean(
                row["is_preferred_supplier"]
            ),
        })

    return records


def main():
    print("Starting Product-Supplier Bridge Load...")

    relationships = read_relationships()

    print(
        f"Source relationships validated: {len(relationships)}"
    )

    engine = get_database_engine()

    inserted_count = 0

    with engine.begin() as connection:

        for relationship in relationships:
            result = connection.execute(
                INSERT_BRIDGE_SQL,
                relationship
            )

            inserted_count += result.rowcount

    skipped_count = len(relationships) - inserted_count

    print("\nBridge Load Summary")
    print("-------------------")
    print(f"Source relationships: {len(relationships)}")
    print(f"Inserted:             {inserted_count}")
    print(f"Skipped:              {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
