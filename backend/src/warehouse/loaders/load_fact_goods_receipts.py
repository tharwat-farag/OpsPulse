
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STAGING_TABLE = "stg_goods_receipts"
CHUNK_SIZE = 1000

REQUIRED_COLUMNS = [
    "receipt_id",
    "po_line_id",
    "received_date",
    "received_qty",
    "accepted_qty",
    "rejected_qty",
    "po_id",
    "order_date",
    "expected_delivery_date",
    "days_from_order",
    "days_after_expected",
    "is_late_receipt",
    "is_fully_accepted",
    "acceptance_rate",
]

DATE_COLUMNS = [
    "received_date",
    "order_date",
    "expected_delivery_date",
]

NUMERIC_COLUMNS = [
    "received_qty",
    "accepted_qty",
    "rejected_qty",
    "days_from_order",
    "days_after_expected",
    "acceptance_rate",
]

BOOLEAN_COLUMNS = [
    "is_late_receipt",
    "is_fully_accepted",
]


# =========================================================
# 1. READ AND VALIDATE SOURCE DATA
# =========================================================

def get_source_file(batch_id: str) -> Path:

    if not batch_id or not batch_id.strip():
        raise ValueError("A valid batch_id is required.")

    batch_path = Path(batch_id)

    if batch_path.is_absolute() or len(batch_path.parts) != 1:
        raise ValueError("Invalid batch_id path.")

    if batch_id in {".", ".."}:
        raise ValueError("Invalid batch_id path.")

    return (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "goods_receipts.csv"
    )


def read_source_data(batch_id: str) -> pd.DataFrame:

    source_file = get_source_file(batch_id)

    if not source_file.exists():
        raise FileNotFoundError(
            f"Silver source file not found: {source_file}"
        )

    df = pd.read_csv(source_file)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    if df.empty:
        raise ValueError(
            "Goods Receipts source is empty."
        )

    # Validate mandatory values.
    if df.isnull().any().any():

        null_columns = (
            df.columns[df.isnull().any()]
            .tolist()
        )

        raise ValueError(
            f"Null values found in required columns: {null_columns}"
        )

    # Validate unique receipt identifiers.
    duplicate_receipts = (
        df["receipt_id"].duplicated().sum()
    )

    if duplicate_receipts:
        raise ValueError(
            f"Duplicate receipt_id values found: {duplicate_receipts}"
        )

    # Parse dates.
    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(
            df[column],
            errors="raise",
        ).dt.date

    # Enforce numeric data types.
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="raise",
        )

    # Validate boolean columns.
    for column in BOOLEAN_COLUMNS:

        if not df[column].isin([True, False]).all():
            raise ValueError(
                f"Invalid boolean values found in {column}."
            )

    # Validate quantities.
    quantity_columns = [
        "received_qty",
        "accepted_qty",
        "rejected_qty",
    ]

    for column in quantity_columns:

        if (df[column] < 0).any():
            raise ValueError(
                f"Negative values found in {column}."
            )

    if (df["received_qty"] <= 0).any():
        raise ValueError(
            "received_qty must be greater than zero."
        )

    invalid_quantity_rows = (
        df["received_qty"]
        != df["accepted_qty"] + df["rejected_qty"]
    ).sum()

    if invalid_quantity_rows:
        raise ValueError(
            "Received quantity does not equal accepted + rejected "
            f"in {invalid_quantity_rows} rows."
        )

    if (df["accepted_qty"] > df["received_qty"]).any():
        raise ValueError(
            "accepted_qty cannot exceed received_qty."
        )

    if (df["rejected_qty"] > df["received_qty"]).any():
        raise ValueError(
            "rejected_qty cannot exceed received_qty."
        )

    # Validate acceptance rate.
    calculated_rate = (
        df["accepted_qty"] / df["received_qty"]
    )

    invalid_rate_rows = (
        (df["acceptance_rate"] - calculated_rate).abs() > 0.0001
    ).sum()

    if invalid_rate_rows:
        raise ValueError(
            f"Invalid acceptance_rate in {invalid_rate_rows} rows."
        )

    if not df["acceptance_rate"].between(0, 1).all():
        raise ValueError(
            "acceptance_rate must be between 0 and 1."
        )

    # Validate date-related attributes.
    calculated_days_from_order = (
        pd.to_datetime(df["received_date"])
        - pd.to_datetime(df["order_date"])
    ).dt.days

    if not (
        calculated_days_from_order == df["days_from_order"]
    ).all():
        raise ValueError(
            "days_from_order validation failed."
        )

    calculated_days_after_expected = (
        pd.to_datetime(df["received_date"])
        - pd.to_datetime(df["expected_delivery_date"])
    ).dt.days

    if not (
        calculated_days_after_expected == df["days_after_expected"]
    ).all():
        raise ValueError(
            "days_after_expected validation failed."
        )

    expected_late_flag = (
        df["days_after_expected"] > 0
    )

    if not (
        expected_late_flag == df["is_late_receipt"]
    ).all():
        raise ValueError(
            "is_late_receipt validation failed."
        )

    expected_fully_accepted = (
        df["accepted_qty"] == df["received_qty"]
    )

    if not (
        expected_fully_accepted == df["is_fully_accepted"]
    ).all():
        raise ValueError(
            "is_fully_accepted validation failed."
        )

    if (df["days_from_order"] < 0).any():
        raise ValueError(
            "Receipt date cannot precede order date."
        )

    print(f"Batch ID: {batch_id}")
    print(f"Source records: {len(df):,}")
    print("Source validation: PASSED")

    return df


# =========================================================
# 2. LOAD SOURCE DATA INTO STAGING
# =========================================================

def load_to_staging(
    engine,
    df: pd.DataFrame,
) -> None:

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
# 3. VALIDATE PURCHASE ORDER LINE RELATIONSHIPS
# =========================================================

def validate_po_relationships(engine) -> None:

    relationship_sql = text("""
        SELECT
            COUNT(*) AS source_rows,

            COUNT(*) FILTER (
                WHERE pol.po_line_id IS NULL
            ) AS missing_po_lines,

            COUNT(*) FILTER (
                WHERE pol.po_id IS DISTINCT FROM s.po_id
            ) AS mismatched_po_ids,

            COUNT(*) FILTER (
                WHERE pol.po_line_id IS NOT NULL
                  AND pol.product_key IS NULL
            ) AS missing_product_keys,

            COUNT(*) FILTER (
                WHERE pol.po_line_id IS NOT NULL
                  AND pol.supplier_key IS NULL
            ) AS missing_supplier_keys

        FROM staging.stg_goods_receipts s

        LEFT JOIN gold.fact_purchase_order_lines pol
            ON pol.po_line_id = s.po_line_id;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            relationship_sql
        ).mappings().one()

    print("\nPurchase Order relationship validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    invalid_columns = [
        "missing_po_lines",
        "mismatched_po_ids",
        "missing_product_keys",
        "missing_supplier_keys",
    ]

    if any(result[column] != 0 for column in invalid_columns):
        raise ValueError(
            "Goods Receipt to Purchase Order Line "
            "relationship validation failed."
        )

    print("Purchase Order relationship validation: PASSED")


# =========================================================
# 4. VALIDATE DATE DIMENSION RELATIONSHIPS
# =========================================================

def validate_date_dimensions(engine) -> None:

    date_sql = text("""
        SELECT
            COUNT(*) FILTER (
                WHERE rd.date_key IS NULL
            ) AS invalid_received_dates,

            COUNT(*) FILTER (
                WHERE od.date_key IS NULL
            ) AS invalid_order_dates,

            COUNT(*) FILTER (
                WHERE ed.date_key IS NULL
            ) AS invalid_expected_dates

        FROM staging.stg_goods_receipts s

        LEFT JOIN gold.dim_date rd
            ON rd.full_date = s.received_date

        LEFT JOIN gold.dim_date od
            ON od.full_date = s.order_date

        LEFT JOIN gold.dim_date ed
            ON ed.full_date = s.expected_delivery_date;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            date_sql
        ).mappings().one()

    print("\nDate dimension validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    if any(value != 0 for value in result.values()):
        raise ValueError(
            "One or more dates do not exist in dim_date."
        )

    print("Date dimension validation: PASSED")


# =========================================================
# 5. VALIDATE PURCHASE ORDER DATE CONSISTENCY
# =========================================================

def validate_po_dates(engine) -> None:

    po_date_sql = text("""
        SELECT
            COUNT(*) AS mismatched_po_dates

        FROM staging.stg_goods_receipts s

        JOIN gold.fact_purchase_order_lines pol
            ON pol.po_line_id = s.po_line_id

        JOIN gold.dim_date od
            ON od.date_key = pol.order_date_key

        JOIN gold.dim_date ed
            ON ed.date_key = pol.expected_delivery_date_key

        WHERE od.full_date <> s.order_date
           OR ed.full_date <> s.expected_delivery_date;
    """)

    with engine.connect() as connection:

        mismatched_dates = connection.execute(
            po_date_sql
        ).scalar_one()

    print(
        "\nMismatched Purchase Order dates:",
        mismatched_dates,
    )

    if mismatched_dates != 0:
        raise ValueError(
            "Source PO dates do not match Gold PO line dates."
        )

    print("Purchase Order date validation: PASSED")


# =========================================================
# 6. LOAD FACT GOODS RECEIPTS
# =========================================================

def load_fact_goods_receipts(engine) -> None:

    insert_sql = text("""
        INSERT INTO gold.fact_goods_receipts (
            receipt_id,
            po_id,
            po_line_id,

            received_date_key,
            order_date_key,
            expected_delivery_date_key,

            product_key,
            supplier_key,

            received_qty,
            accepted_qty,
            rejected_qty,

            acceptance_rate,

            days_from_order,
            days_after_expected,

            is_late_receipt,
            is_fully_accepted
        )

        SELECT
            s.receipt_id,
            s.po_id,
            s.po_line_id,

            rd.date_key,
            od.date_key,
            ed.date_key,

            pol.product_key,
            pol.supplier_key,

            s.received_qty,
            s.accepted_qty,
            s.rejected_qty,

            s.acceptance_rate,

            s.days_from_order,
            s.days_after_expected,

            s.is_late_receipt,
            s.is_fully_accepted

        FROM staging.stg_goods_receipts s

        JOIN gold.fact_purchase_order_lines pol
            ON pol.po_line_id = s.po_line_id

        JOIN gold.dim_date rd
            ON rd.full_date = s.received_date

        JOIN gold.dim_date od
            ON od.full_date = s.order_date

        JOIN gold.dim_date ed
            ON ed.full_date = s.expected_delivery_date

        ON CONFLICT (receipt_id) DO NOTHING;
    """)

    with engine.begin() as connection:

        insert_result = connection.execute(
            insert_sql
        )

    print("\nFact Goods Receipts load:")
    print(f"Records inserted: {insert_result.rowcount}")


# =========================================================
# 7. RECONCILE SILVER AND GOLD
# =========================================================

def reconcile_goods_receipts(engine) -> None:

    reconciliation_sql = text("""
        WITH comparison AS (

            SELECT
                s.receipt_id,

                f.receipt_id AS matched_receipt_id,

                (
                    f.po_id IS DISTINCT FROM s.po_id

                    OR f.po_line_id IS DISTINCT FROM s.po_line_id

                    OR f.received_qty IS DISTINCT FROM s.received_qty

                    OR f.accepted_qty IS DISTINCT FROM s.accepted_qty

                    OR f.rejected_qty IS DISTINCT FROM s.rejected_qty

                    OR f.acceptance_rate IS DISTINCT FROM s.acceptance_rate

                    OR f.days_from_order IS DISTINCT FROM s.days_from_order

                    OR f.days_after_expected IS DISTINCT FROM s.days_after_expected

                    OR f.is_late_receipt IS DISTINCT FROM s.is_late_receipt

                    OR f.is_fully_accepted IS DISTINCT FROM s.is_fully_accepted

                    OR f.product_key IS DISTINCT FROM pol.product_key

                    OR f.supplier_key IS DISTINCT FROM pol.supplier_key

                    OR f.received_date_key IS DISTINCT FROM rd.date_key

                    OR f.order_date_key IS DISTINCT FROM od.date_key

                    OR f.expected_delivery_date_key IS DISTINCT FROM ed.date_key

                ) AS has_mismatch,

                s.received_qty AS source_received_qty,
                s.accepted_qty AS source_accepted_qty,
                s.rejected_qty AS source_rejected_qty,

                f.received_qty AS gold_received_qty,
                f.accepted_qty AS gold_accepted_qty,
                f.rejected_qty AS gold_rejected_qty

            FROM staging.stg_goods_receipts s

            LEFT JOIN gold.fact_goods_receipts f
                ON f.receipt_id = s.receipt_id

            LEFT JOIN gold.fact_purchase_order_lines pol
                ON pol.po_line_id = s.po_line_id

            LEFT JOIN gold.dim_date rd
                ON rd.full_date = s.received_date

            LEFT JOIN gold.dim_date od
                ON od.full_date = s.order_date

            LEFT JOIN gold.dim_date ed
                ON ed.full_date = s.expected_delivery_date
        )

        SELECT

            COUNT(*) AS source_rows,

            COUNT(matched_receipt_id) AS matched_fact_rows,

            COUNT(*) FILTER (
                WHERE matched_receipt_id IS NULL
            ) AS missing_fact_rows,

            COUNT(*) FILTER (
                WHERE matched_receipt_id IS NOT NULL
                  AND has_mismatch
            ) AS mismatched_rows,

            COALESCE(SUM(source_received_qty), 0)
                AS source_received_qty,

            COALESCE(SUM(source_accepted_qty), 0)
                AS source_accepted_qty,

            COALESCE(SUM(source_rejected_qty), 0)
                AS source_rejected_qty,

            COALESCE(SUM(gold_received_qty), 0)
                AS gold_received_qty,

            COALESCE(SUM(gold_accepted_qty), 0)
                AS gold_accepted_qty,

            COALESCE(SUM(gold_rejected_qty), 0)
                AS gold_rejected_qty

        FROM comparison;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value}")

    # Row-level reconciliation.
    if (
        result["source_rows"] != result["matched_fact_rows"]
        or result["missing_fact_rows"] != 0
        or result["mismatched_rows"] != 0
    ):
        raise ValueError(
            "Silver-to-Gold row-level reconciliation failed."
        )

    # Quantity reconciliation.
    quantity_checks = [
        (
            "source_received_qty",
            "gold_received_qty",
        ),
        (
            "source_accepted_qty",
            "gold_accepted_qty",
        ),
        (
            "source_rejected_qty",
            "gold_rejected_qty",
        ),
    ]

    for source_column, gold_column in quantity_checks:

        if result[source_column] != result[gold_column]:
            raise ValueError(
                f"Quantity reconciliation failed: {source_column}"
            )

    # Global uniqueness check for receipt identifiers.
    fact_check_sql = text("""
        SELECT
            COUNT(*) AS fact_rows,

            COUNT(DISTINCT receipt_id) AS unique_receipts

        FROM gold.fact_goods_receipts;
    """)

    with engine.connect() as connection:

        fact_check = connection.execute(
            fact_check_sql
        ).mappings().one()

    print("\nGold Fact totals:")

    for key, value in fact_check.items():
        print(f"{key}: {value:,}")

    if fact_check["fact_rows"] != fact_check["unique_receipts"]:
        raise ValueError(
            "Duplicate receipt IDs detected in Gold."
        )

    print("\nSilver-to-Gold reconciliation: PASSED")


# =========================================================
# 8. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError(
            "A valid batch_id is required."
        )

    print("=" * 60)
    print("OPSPULSE - FACT GOODS RECEIPTS LOADER")
    print(f"Batch ID: {batch_id}")
    print("=" * 60)

    engine = get_database_engine()

    try:

        # Step 1: Read and validate Silver data.
        df = read_source_data(batch_id)

        # Step 2: Load data into Staging.
        load_to_staging(engine, df)

        # Step 3: Validate Purchase Order relationships.
        validate_po_relationships(engine)

        # Step 4: Validate Date dimensions.
        validate_date_dimensions(engine)

        # Step 5: Validate Purchase Order dates.
        validate_po_dates(engine)

        print("\nDimension and relationship validation: PASSED")

        # Step 6: Load Gold Fact.
        load_fact_goods_receipts(engine)

        # Step 7: Reconcile current Batch.
        reconcile_goods_receipts(engine)

        print("\n" + "=" * 60)
        print("FACT GOODS RECEIPTS LOAD COMPLETED SUCCESSFULLY.")
        print("=" * 60)

    finally:
        engine.dispose()


# =========================================================
# 9. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Goods Receipts data into Gold."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
