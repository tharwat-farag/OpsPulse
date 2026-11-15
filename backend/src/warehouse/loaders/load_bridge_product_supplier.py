
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]

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


VALIDATE_DIMENSIONS_SQL = text("""
    SELECT
        source.product_id,
        source.supplier_id
    FROM (
        SELECT
            :product_id AS product_id,
            :supplier_id AS supplier_id
    ) AS source
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.dim_product AS product
        WHERE product.product_id = source.product_id
          AND product.is_current = TRUE
    )
    OR NOT EXISTS (
        SELECT 1
        FROM gold.dim_supplier AS supplier
        WHERE supplier.supplier_id = source.supplier_id
          AND supplier.is_current = TRUE
    )
""")


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_relationships(batch_id: str) -> list[dict]:
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must not be empty.")

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "product_suppliers.csv"
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

        relationships = list(reader)

    if not relationships:
        raise ValueError("Source file contains no relationships.")

    pairs = []
    records = []

    for row in relationships:
        product_id = (row["product_id"] or "").strip()
        supplier_id = (row["supplier_id"] or "").strip()

        if not product_id or not supplier_id:
            raise ValueError(
                "Product ID and Supplier ID must not be empty."
            )

        pairs.append((product_id, supplier_id))

        try:
            supplier_price = Decimal(
                row["supplier_price"].strip()
            )
            lead_time_days = int(row["lead_time_days"].strip())
            minimum_order_qty = int(
                row["minimum_order_qty"].strip()
            )
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid numeric values for "
                f"{product_id}/{supplier_id}"
            ) from exc

        if not supplier_price.is_finite() or supplier_price < 0:
            raise ValueError(
                f"Invalid supplier price for "
                f"{product_id}/{supplier_id}"
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

    if len(pairs) != len(set(pairs)):
        raise ValueError("Duplicate product-supplier pair found.")

    return records


def main(batch_id: str) -> None:
    print("Starting Product-Supplier Bridge Load...")
    print(f"Batch ID: {batch_id}")

    relationships = read_relationships(batch_id)

    print(
        f"Source relationships validated: {len(relationships)}"
    )

    engine = get_database_engine()

    try:
        inserted_count = 0
        skipped_count = 0

        with engine.begin() as connection:

            missing_dimensions = []

            for relationship in relationships:
                missing = connection.execute(
                    VALIDATE_DIMENSIONS_SQL,
                    relationship
                ).fetchone()

                if missing:
                    missing_dimensions.append(
                        f"{relationship['product_id']}/"
                        f"{relationship['supplier_id']}"
                    )

            if missing_dimensions:
                raise ValueError(
                    "Missing current Product/Supplier dimension records: "
                    + ", ".join(missing_dimensions)
                )

            for relationship in relationships:
                result = connection.execute(
                    INSERT_BRIDGE_SQL,
                    relationship
                )

                if result.rowcount == 1:
                    inserted_count += 1
                else:
                    skipped_count += 1

        print("\nProduct-Supplier Bridge Load Summary")
        print("------------------------------------")
        print(f"Source relationships: {len(relationships)}")
        print(f"Inserted:              {inserted_count}")
        print(f"Already existing:      {skipped_count}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Load Product-Supplier Bridge from a Silver batch."
        )
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Silver batch ID to load."
    )

    args = parser.parse_args()
    main(args.batch_id)
