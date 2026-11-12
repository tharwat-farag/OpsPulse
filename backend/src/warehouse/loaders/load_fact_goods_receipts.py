
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# ---------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "goods_receipts.csv"
)

STAGING_TABLE = "stg_goods_receipts"


# ---------------------------------------------------------
# 2. Source validation
# ---------------------------------------------------------

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


def load_source_data() -> pd.DataFrame:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Silver source file not found: {SOURCE_FILE}"
        )

    df = pd.read_csv(SOURCE_FILE)

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
        raise ValueError("Goods Receipts source is empty.")

    # Check mandatory values.
    if df.isnull().any().any():
        null_columns = (
            df.columns[df.isnull().any()]
            .tolist()
        )
        raise ValueError(
            f"Null values found in required columns: {null_columns}"
        )

    # Check unique receipt identifiers.
    duplicate_receipts = df["receipt_id"].duplicated().sum()

    if duplicate_receipts:
        raise ValueError(
            f"Duplicate receipt_id values found: {duplicate_receipts}"
        )

    # Parse dates.
    date_columns = [
        "received_date",
        "order_date",
        "expected_delivery_date",
    ]

    for column in date_columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="raise"
        ).dt.date

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
        raise ValueError("received_qty must be greater than zero.")

    invalid_quantity_rows = (
        df["received_qty"]
        != df["accepted_qty"] + df["rejected_qty"]
    ).sum()

    if invalid_quantity_rows:
        raise ValueError(
            "Received quantity does not equal accepted + rejected "
            f"in {invalid_quantity_rows} rows."
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
        raise ValueError("acceptance_rate must be between 0 and 1.")

    # Validate date-related attributes.
    calculated_days_from_order = (
        pd.to_datetime(df["received_date"])
        - pd.to_datetime(df["order_date"])
    ).dt.days

    if not (
        calculated_days_from_order == df["days_from_order"]
    ).all():
        raise ValueError("days_from_order validation failed.")

    calculated_days_after_expected = (
        pd.to_datetime(df["received_date"])
        - pd.to_datetime(df["expected_delivery_date"])
    ).dt.days

    if not (
        calculated_days_after_expected == df["days_after_expected"]
    ).all():
        raise ValueError("days_after_expected validation failed.")

    expected_late_flag = (
        df["days_after_expected"] > 0
    )

    if not (
        expected_late_flag == df["is_late_receipt"]
    ).all():
        raise ValueError("is_late_receipt validation failed.")

    expected_fully_accepted = (
        df["accepted_qty"] == df["received_qty"]
    )

    if not (
        expected_fully_accepted == df["is_fully_accepted"]
    ).all():
        raise ValueError("is_fully_accepted validation failed.")

    if (df["days_from_order"] < 0).any():
        raise ValueError("Receipt date cannot precede order date.")

    print(f"Source records: {len(df):,}")
    print("Source validation: PASSED")

    return df


# ---------------------------------------------------------
# 3. Database loading
# ---------------------------------------------------------

def load_fact_goods_receipts() -> None:
    df = load_source_data()
    engine = get_database_engine()

    try:
        with engine.begin() as connection:

            # ---------------------------------------------
            # Load source records into staging.
            # ---------------------------------------------

            df.to_sql(
                name=STAGING_TABLE,
                schema="staging",
                con=connection,
                if_exists="replace",
                index=False,
                chunksize=1000,
                method="multi",
            )

            print("Staging load: COMPLETED")

            # ---------------------------------------------
            # Validate PO line relationships.
            # ---------------------------------------------

            relationship_check = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS source_rows,

                        COUNT(*) FILTER (
                            WHERE pol.po_line_id IS NULL
                        ) AS missing_po_lines,

                        COUNT(*) FILTER (
                            WHERE pol.po_id IS DISTINCT FROM s.po_id
                        ) AS mismatched_po_ids

                    FROM staging.stg_goods_receipts s

                    LEFT JOIN gold.fact_purchase_order_lines pol
                        ON pol.po_line_id = s.po_line_id;
                """)
            ).mappings().one()

            print(
                "Missing PO lines:",
                relationship_check["missing_po_lines"]
            )

            print(
                "Mismatched PO IDs:",
                relationship_check["mismatched_po_ids"]
            )

            if (
                relationship_check["missing_po_lines"] != 0
                or relationship_check["mismatched_po_ids"] != 0
            ):
                raise ValueError(
                    "Goods Receipt to Purchase Order Line "
                    "relationship validation failed."
                )

            # ---------------------------------------------
            # Validate date dimension relationships.
            # ---------------------------------------------

            date_check = connection.execute(
                text("""
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
            ).mappings().one()

            print("Date dimension validation:")
            print(dict(date_check))

            if any(value != 0 for value in date_check.values()):
                raise ValueError(
                    "One or more dates do not exist in dim_date."
                )

            # ---------------------------------------------
            # Validate PO date consistency.
            # ---------------------------------------------

            po_date_check = connection.execute(
                text("""
                    SELECT COUNT(*) AS mismatched_po_dates

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
            ).scalar_one()

            print("Mismatched PO dates:", po_date_check)

            if po_date_check != 0:
                raise ValueError(
                    "Source PO dates do not match Gold PO line dates."
                )

            print("Dimension matching: PASSED")

            # ---------------------------------------------
            # Insert records into Gold Fact.
            # ---------------------------------------------

            insert_result = connection.execute(
                text("""
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
            )

            print(
                "Records inserted:",
                insert_result.rowcount
            )

            # ---------------------------------------------
            # Reconciliation.
            # Compare every source receipt with its Gold row.
            # ---------------------------------------------

            reconciliation = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS source_rows,

                        COUNT(f.receipt_id) AS matched_fact_rows,

                        COUNT(*) FILTER (
                            WHERE f.receipt_id IS NULL
                        ) AS missing_fact_rows,

                        COUNT(*) FILTER (
                            WHERE f.receipt_id IS NOT NULL
                              AND (
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
                              )
                        ) AS mismatched_rows,

                        COALESCE(SUM(s.received_qty), 0)
                            AS source_received_qty,

                        COALESCE(SUM(s.accepted_qty), 0)
                            AS source_accepted_qty,

                        COALESCE(SUM(s.rejected_qty), 0)
                            AS source_rejected_qty,

                        COALESCE(SUM(f.received_qty), 0)
                            AS gold_received_qty,

                        COALESCE(SUM(f.accepted_qty), 0)
                            AS gold_accepted_qty,

                        COALESCE(SUM(f.rejected_qty), 0)
                            AS gold_rejected_qty

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
                        ON ed.full_date = s.expected_delivery_date;
                """)
            ).mappings().one()

            print("\nReconciliation results:")

            for key, value in reconciliation.items():
                print(f"{key}: {value}")

            # ---------------------------------------------
            # Final count and uniqueness checks.
            # ---------------------------------------------

            fact_check = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS fact_rows,
                        COUNT(DISTINCT receipt_id) AS unique_receipts,
                        COUNT(DISTINCT po_line_id) AS unique_po_lines
                    FROM gold.fact_goods_receipts;
                """)
            ).mappings().one()

            print("\nGold Fact totals:")
            print(dict(fact_check))

            if (
                reconciliation["source_rows"]
                != reconciliation["matched_fact_rows"]
                or reconciliation["missing_fact_rows"] != 0
                or reconciliation["mismatched_rows"] != 0
            ):
                raise ValueError(
                    "Silver-to-Gold row-level reconciliation failed."
                )

            for source_column, gold_column in [
                ("source_received_qty", "gold_received_qty"),
                ("source_accepted_qty", "gold_accepted_qty"),
                ("source_rejected_qty", "gold_rejected_qty"),
            ]:
                if (
                    reconciliation[source_column]
                    != reconciliation[gold_column]
                ):
                    raise ValueError(
                        f"Quantity reconciliation failed: {source_column}"
                    )

            if (
                fact_check["fact_rows"]
                != fact_check["unique_receipts"]
            ):
                raise ValueError(
                    "Duplicate receipt IDs detected in Gold."
                )

            print("\nSilver-to-Gold reconciliation: PASSED")

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_fact_goods_receipts()
