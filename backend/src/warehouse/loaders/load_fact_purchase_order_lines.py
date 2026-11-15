
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STAGING_TABLE = "stg_purchase_order_lines"
CHUNK_SIZE = 1000

LINE_COLUMNS = [
    "po_line_id",
    "po_id",
    "product_id",
    "ordered_qty",
    "unit_cost",
    "line_total",
    "is_high_value_line",
]

ORDER_COLUMNS = [
    "po_id",
    "supplier_id",
    "order_date",
    "expected_delivery_date",
    "status",
]


# =========================================================
# SOURCE FILE PATHS
# =========================================================

def get_source_files(batch_id: str) -> tuple[Path, Path]:
    """Build Silver source file paths using the provided batch ID."""

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must be provided.")

    silver_dir = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
    )

    return (
        silver_dir / "purchase_order_lines.csv",
        silver_dir / "purchase_orders.csv",
    )


# =========================================================
# 1. READ AND VALIDATE SOURCE FILES
# =========================================================

def read_source_data(batch_id: str):
    lines_file, orders_file = get_source_files(batch_id)

    if not lines_file.exists():
        raise FileNotFoundError(f"Missing file: {lines_file}")

    if not orders_file.exists():
        raise FileNotFoundError(f"Missing file: {orders_file}")

    lines = pd.read_csv(lines_file)
    orders = pd.read_csv(orders_file)

    # Validate columns before parsing dates.
    for column in LINE_COLUMNS:
        if column not in lines.columns:
            raise ValueError(f"Missing line column: {column}")

    for column in ORDER_COLUMNS:
        if column not in orders.columns:
            raise ValueError(f"Missing order column: {column}")

    if lines.empty or orders.empty:
        raise ValueError("Source files cannot be empty.")

    # Parse dates after validating their existence.
    orders["order_date"] = pd.to_datetime(
        orders["order_date"],
        errors="raise",
    )

    orders["expected_delivery_date"] = pd.to_datetime(
        orders["expected_delivery_date"],
        errors="raise",
    )

    if lines[LINE_COLUMNS].isnull().any().any():
        raise ValueError(
            "Required purchase line values contain NULL."
        )

    if orders[ORDER_COLUMNS].isnull().any().any():
        raise ValueError(
            "Required purchase order values contain NULL."
        )

    if lines["po_line_id"].duplicated().any():
        raise ValueError("Duplicate po_line_id detected.")

    if orders["po_id"].duplicated().any():
        raise ValueError(
            "Duplicate po_id detected in purchase orders."
        )

    if (lines["ordered_qty"] <= 0).any():
        raise ValueError("Invalid ordered quantity.")

    if (lines["unit_cost"] < 0).any():
        raise ValueError("Negative unit cost detected.")

    if (lines["line_total"] < 0).any():
        raise ValueError("Negative line total detected.")

    print(f"Batch ID: {batch_id}")
    print(f"Purchase order lines: {len(lines):,}")
    print(f"Purchase orders: {len(orders):,}")
    print("Source validation: PASSED")

    return lines, orders


# =========================================================
# 2. JOIN HEADER AND LINE DATA
# =========================================================

def integrate_purchase_data(lines, orders):

    integrated = lines.merge(
        orders[ORDER_COLUMNS],
        on="po_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched = integrated[
        integrated["_merge"] != "both"
    ]

    if not unmatched.empty:
        raise ValueError(
            f"{len(unmatched)} purchase lines have no matching order."
        )

    integrated.drop(columns=["_merge"], inplace=True)

    if len(integrated) != len(lines):
        raise ValueError(
            "Unexpected row count change after joining source files."
        )

    print("\nSource integration:")
    print(f"Integrated records: {len(integrated):,}")
    print("Header-to-lines relationship: PASSED")

    return integrated


# =========================================================
# 3. LOAD STAGING
# =========================================================

def load_to_staging(engine, df):

    print("\nLoading data into Staging...")

    with engine.begin() as connection:

        df.to_sql(
            name=STAGING_TABLE,
            schema="staging",
            con=connection,
            if_exists="replace",
            index=False,
            chunksize=CHUNK_SIZE,
            method="multi",
        )

    print("Staging load: COMPLETED")


# =========================================================
# 4. VALIDATE DIMENSION MATCHES
# =========================================================

def validate_dimension_matches(engine):

    validation_sql = text("""
        SELECT
            COUNT(*) AS source_rows,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_date d
                    WHERE d.full_date = s.order_date::date
                ) <> 1
            ) AS invalid_order_dates,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_date d
                    WHERE d.full_date = s.expected_delivery_date::date
                ) <> 1
            ) AS invalid_expected_dates,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_product p
                    WHERE p.product_id = s.product_id
                      AND p.valid_from <= s.order_date::date
                      AND s.order_date::date < p.valid_to
                ) <> 1
            ) AS invalid_products,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_supplier sp
                    WHERE sp.supplier_id = s.supplier_id
                      AND sp.valid_from <= s.order_date::date
                      AND s.order_date::date < sp.valid_to
                ) <> 1
            ) AS invalid_suppliers

        FROM staging.stg_purchase_order_lines s;
    """)

    with engine.connect() as connection:
        result = connection.execute(
            validation_sql
        ).mappings().one()

    print("\nDimension matching validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    invalid_columns = [
        "invalid_order_dates",
        "invalid_expected_dates",
        "invalid_products",
        "invalid_suppliers",
    ]

    if any(result[column] > 0 for column in invalid_columns):
        raise ValueError("Dimension matching failed.")

    print("Dimension matching: PASSED")


# =========================================================
# 5. LOAD FACT TABLE
# =========================================================

def load_fact_purchase_order_lines(engine):

    insert_sql = text("""
        INSERT INTO gold.fact_purchase_order_lines (
            po_line_id,
            po_id,
            order_date_key,
            expected_delivery_date_key,
            product_key,
            supplier_key,
            ordered_qty,
            unit_cost,
            line_total,
            order_status,
            is_high_value_line
        )

        SELECT
            s.po_line_id,
            s.po_id,
            order_date.date_key,
            expected_date.date_key,
            p.product_key,
            sp.supplier_key,
            s.ordered_qty,
            s.unit_cost,
            s.line_total,
            s.status,
            s.is_high_value_line

        FROM staging.stg_purchase_order_lines s

        INNER JOIN gold.dim_date order_date
            ON order_date.full_date = s.order_date::date

        INNER JOIN gold.dim_date expected_date
            ON expected_date.full_date =
               s.expected_delivery_date::date

        INNER JOIN gold.dim_product p
            ON p.product_id = s.product_id
           AND p.valid_from <= s.order_date::date
           AND s.order_date::date < p.valid_to

        INNER JOIN gold.dim_supplier sp
            ON sp.supplier_id = s.supplier_id
           AND sp.valid_from <= s.order_date::date
           AND s.order_date::date < sp.valid_to

        ON CONFLICT (po_line_id) DO NOTHING;
    """)

    with engine.begin() as connection:

        before_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_purchase_order_lines
            """)
        ).scalar_one()

        connection.execute(insert_sql)

        after_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_purchase_order_lines
            """)
        ).scalar_one()

    print("\nFact Purchase Order Lines load:")
    print(f"Records inserted: {after_count - before_count:,}")
    print(f"Total records: {after_count:,}")


# =========================================================
# 6. SILVER-TO-GOLD RECONCILIATION
# =========================================================

def reconcile_purchase_lines(engine):

    reconciliation_sql = text("""
        WITH comparison AS (

            SELECT
                s.po_line_id,

                f.po_line_id AS fact_po_line_id,

                (
                    f.po_id IS DISTINCT FROM s.po_id

                    OR f.ordered_qty IS DISTINCT FROM s.ordered_qty

                    OR f.unit_cost IS DISTINCT FROM s.unit_cost

                    OR f.line_total IS DISTINCT FROM s.line_total

                    OR f.order_status IS DISTINCT FROM s.status

                    OR f.is_high_value_line
                       IS DISTINCT FROM s.is_high_value_line

                    OR order_date.full_date
                       IS DISTINCT FROM s.order_date::date

                    OR expected_date.full_date
                       IS DISTINCT FROM
                          s.expected_delivery_date::date

                    OR p.product_id IS DISTINCT FROM s.product_id

                    OR sp.supplier_id IS DISTINCT FROM s.supplier_id

                ) AS has_mismatch

            FROM staging.stg_purchase_order_lines s

            LEFT JOIN gold.fact_purchase_order_lines f
                ON f.po_line_id = s.po_line_id

            LEFT JOIN gold.dim_date order_date
                ON order_date.date_key = f.order_date_key

            LEFT JOIN gold.dim_date expected_date
                ON expected_date.date_key =
                   f.expected_delivery_date_key

            LEFT JOIN gold.dim_product p
                ON p.product_key = f.product_key

            LEFT JOIN gold.dim_supplier sp
                ON sp.supplier_key = f.supplier_key
        )

        SELECT
            COUNT(*) AS source_rows,

            COUNT(fact_po_line_id) AS matched_fact_rows,

            COUNT(*) FILTER (
                WHERE fact_po_line_id IS NULL
            ) AS missing_fact_rows,

            COUNT(*) FILTER (
                WHERE fact_po_line_id IS NOT NULL
                  AND has_mismatch
            ) AS mismatched_fact_rows

        FROM comparison;
    """)

    with engine.connect() as connection:
        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    if result["source_rows"] != result["matched_fact_rows"]:
        raise ValueError(
            "Silver-to-Gold row count reconciliation failed."
        )

    if result["missing_fact_rows"] > 0:
        raise ValueError(
            "Some purchase order lines are missing from Gold."
        )

    if result["mismatched_fact_rows"] > 0:
        raise ValueError(
            "Purchase order line values differ between Silver and Gold."
        )

    print("Silver-to-Gold reconciliation: PASSED")


# =========================================================
# 7. MAIN
# =========================================================

def main(batch_id: str):

    print("=" * 60)
    print("OPSPULSE - FACT PURCHASE ORDER LINES LOADER")
    print("=" * 60)

    print(f"Processing batch: {batch_id}")

    engine = get_database_engine()

    try:
        lines, orders = read_source_data(batch_id)

        integrated = integrate_purchase_data(lines, orders)

        load_to_staging(engine, integrated)

        validate_dimension_matches(engine)

        load_fact_purchase_order_lines(engine)

        reconcile_purchase_lines(engine)

        print("\n" + "=" * 60)
        print("FACT PURCHASE ORDER LINES LOAD COMPLETED SUCCESSFULLY.")
        print("=" * 60)

    finally:
        engine.dispose()


# =========================================================
# 8. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load purchase order lines into OpsPulse Gold."
    )

    parser.add_argument(
        "batch_id",
        help="Silver batch ID to load.",
    )

    args = parser.parse_args()

    main(args.batch_id)
