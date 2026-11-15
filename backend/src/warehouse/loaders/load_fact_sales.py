
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STAGING_TABLE = "stg_sales"
CHUNK_SIZE = 1000

REQUIRED_COLUMNS = [
    "sales_line_id",
    "invoice_id",
    "sale_date",
    "product_id",
    "customer_id",
    "branch_id",
    "quantity",
    "unit_price",
    "unit_cost",
    "discount_amount",
    "gross_amount",
    "net_revenue",
    "total_cost",
    "gross_profit",
    "sales_channel",
]


# =========================================================
# 1. READ AND VALIDATE SILVER DATA
# =========================================================

def read_sales_data(batch_id: str) -> pd.DataFrame:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "sales.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Silver sales file not found: {source_file}"
        )

    df = pd.read_csv(
        source_file,
        parse_dates=["sale_date"],
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError("Sales source file is empty.")

    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise ValueError(
            "Sales source contains NULL values "
            "in required columns."
        )

    if df["sales_line_id"].duplicated().any():
        raise ValueError(
            "Duplicate sales_line_id values found in Silver."
        )

    if (df["quantity"] <= 0).any():
        raise ValueError(
            "Sales quantity must be greater than zero."
        )

    print(f"Silver records read: {len(df):,}")
    print("Source validation: PASSED")

    return df


# =========================================================
# 2. LOAD DATA INTO STAGING
# =========================================================

def load_to_staging(
    engine,
    df: pd.DataFrame,
) -> None:

    print("\nLoading data into Staging...")

    with engine.begin() as connection:

        df[REQUIRED_COLUMNS].to_sql(
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
# 3. VALIDATE DIMENSION MATCHES
# =========================================================

def validate_dimension_matches(engine) -> None:

    validation_sql = text("""
        SELECT
            COUNT(*) AS source_rows,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_date d
                    WHERE d.full_date = s.sale_date::date
                ) <> 1
            ) AS invalid_dates,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_product p
                    WHERE p.product_id = s.product_id
                      AND p.valid_from <= s.sale_date::date
                      AND s.sale_date::date < p.valid_to
                ) <> 1
            ) AS invalid_products,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_customer c
                    WHERE c.customer_id = s.customer_id
                      AND c.valid_from <= s.sale_date::date
                      AND s.sale_date::date < c.valid_to
                ) <> 1
            ) AS invalid_customers,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_branch b
                    WHERE b.branch_id = s.branch_id
                      AND b.valid_from <= s.sale_date::date
                      AND s.sale_date::date < b.valid_to
                ) <> 1
            ) AS invalid_branches,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_sales_channel ch
                    WHERE ch.sales_channel_name = s.sales_channel
                ) <> 1
            ) AS invalid_channels

        FROM staging.stg_sales s;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            validation_sql
        ).mappings().one()

    print("\nDimension matching validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    invalid_columns = [
        "invalid_dates",
        "invalid_products",
        "invalid_customers",
        "invalid_branches",
        "invalid_channels",
    ]

    invalid_total = sum(
        result[column]
        for column in invalid_columns
    )

    if invalid_total > 0:
        raise ValueError(
            "Dimension matching failed. "
            "Some records have missing or ambiguous dimension matches."
        )

    print("Dimension matching: PASSED")


# =========================================================
# 4. LOAD FACT SALES
# =========================================================

def load_fact_sales(engine) -> None:

    insert_sql = text("""
        INSERT INTO gold.fact_sales (
            sales_line_id,
            invoice_id,
            date_key,
            product_key,
            customer_key,
            branch_key,
            sales_channel_key,
            quantity,
            unit_price,
            unit_cost,
            gross_amount,
            discount_amount,
            net_revenue,
            total_cost,
            gross_profit
        )

        SELECT
            s.sales_line_id,
            s.invoice_id,
            d.date_key,
            p.product_key,
            c.customer_key,
            b.branch_key,
            ch.sales_channel_key,
            s.quantity,
            s.unit_price,
            s.unit_cost,
            s.gross_amount,
            s.discount_amount,
            s.net_revenue,
            s.total_cost,
            s.gross_profit

        FROM staging.stg_sales s

        INNER JOIN gold.dim_date d
            ON d.full_date = s.sale_date::date

        INNER JOIN gold.dim_product p
            ON p.product_id = s.product_id
           AND p.valid_from <= s.sale_date::date
           AND s.sale_date::date < p.valid_to

        INNER JOIN gold.dim_customer c
            ON c.customer_id = s.customer_id
           AND c.valid_from <= s.sale_date::date
           AND s.sale_date::date < c.valid_to

        INNER JOIN gold.dim_branch b
            ON b.branch_id = s.branch_id
           AND b.valid_from <= s.sale_date::date
           AND s.sale_date::date < b.valid_to

        INNER JOIN gold.dim_sales_channel ch
            ON ch.sales_channel_name = s.sales_channel

        ON CONFLICT (sales_line_id) DO NOTHING;
    """)

    with engine.begin() as connection:

        before_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_sales
            """)
        ).scalar_one()

        connection.execute(insert_sql)

        after_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_sales
            """)
        ).scalar_one()

    inserted = after_count - before_count

    print("\nFact Sales load:")
    print(f"Records inserted: {inserted:,}")
    print(f"Total records in Fact Sales: {after_count:,}")


# =========================================================
# 5. RECONCILE SILVER AND GOLD
# =========================================================

def reconcile_sales(
    engine,
    source_count: int,
) -> None:

    reconciliation_sql = text("""
        SELECT

            COUNT(*) AS source_rows,

            COUNT(DISTINCT s.sales_line_id)
                AS unique_source_lines,

            COUNT(DISTINCT f.sales_line_id)
                AS unique_fact_lines,

            COUNT(*) FILTER (
                WHERE
                    f.sales_line_id IS NULL

                    OR f.invoice_id IS DISTINCT FROM s.invoice_id

                    OR f.date_key IS DISTINCT FROM d.date_key

                    OR f.product_key IS DISTINCT FROM p.product_key

                    OR f.customer_key IS DISTINCT FROM c.customer_key

                    OR f.branch_key IS DISTINCT FROM b.branch_key

                    OR f.sales_channel_key
                        IS DISTINCT FROM ch.sales_channel_key

                    OR f.quantity IS DISTINCT FROM s.quantity

                    OR ABS(
                        f.unit_price - s.unit_price
                    ) > 0.000001

                    OR ABS(
                        f.unit_cost - s.unit_cost
                    ) > 0.000001

                    OR ABS(
                        f.gross_amount - s.gross_amount
                    ) > 0.000001

                    OR ABS(
                        f.discount_amount - s.discount_amount
                    ) > 0.000001

                    OR ABS(
                        f.net_revenue - s.net_revenue
                    ) > 0.000001

                    OR ABS(
                        f.total_cost - s.total_cost
                    ) > 0.000001

                    OR ABS(
                        f.gross_profit - s.gross_profit
                    ) > 0.000001

            ) AS mismatched_rows,

            SUM(s.gross_amount) AS source_gross_amount,

            SUM(f.gross_amount) AS fact_gross_amount,

            SUM(s.discount_amount) AS source_discount_amount,

            SUM(f.discount_amount) AS fact_discount_amount,

            SUM(s.net_revenue) AS source_net_revenue,

            SUM(f.net_revenue) AS fact_net_revenue,

            SUM(s.total_cost) AS source_total_cost,

            SUM(f.total_cost) AS fact_total_cost,

            SUM(s.gross_profit) AS source_gross_profit,

            SUM(f.gross_profit) AS fact_gross_profit

        FROM staging.stg_sales s

        LEFT JOIN gold.fact_sales f
            ON f.sales_line_id = s.sales_line_id

        LEFT JOIN gold.dim_date d
            ON d.full_date = s.sale_date::date

        LEFT JOIN gold.dim_product p
            ON p.product_id = s.product_id
           AND p.valid_from <= s.sale_date::date
           AND s.sale_date::date < p.valid_to

        LEFT JOIN gold.dim_customer c
            ON c.customer_id = s.customer_id
           AND c.valid_from <= s.sale_date::date
           AND s.sale_date::date < c.valid_to

        LEFT JOIN gold.dim_branch b
            ON b.branch_id = s.branch_id
           AND b.valid_from <= s.sale_date::date
           AND s.sale_date::date < b.valid_to

        LEFT JOIN gold.dim_sales_channel ch
            ON ch.sales_channel_name = s.sales_channel;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value}")

    if result["source_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: source row count mismatch."
        )

    if result["unique_source_lines"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate source sales lines."
        )

    if result["unique_fact_lines"] != source_count:
        raise ValueError(
            "Reconciliation failed: missing fact sales lines."
        )

    if result["mismatched_rows"] != 0:
        raise ValueError(
            "Reconciliation failed: Silver and Gold values do not match."
        )

    print("Silver-to-Gold reconciliation: PASSED")


# =========================================================
# 6. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError("A valid batch_id is required.")

    print("=" * 55)
    print("OPSPULSE - FACT SALES LOADER")
    print(f"Batch ID: {batch_id}")
    print("=" * 55)

    engine = get_database_engine()

    try:

        # Step 1: Read Silver data
        df = read_sales_data(batch_id)

        # Step 2: Load Staging
        load_to_staging(engine, df)

        # Step 3: Validate dimensions
        validate_dimension_matches(engine)

        # Step 4: Load Gold Fact
        load_fact_sales(engine)

        # Step 5: Reconcile Silver and Gold
        reconcile_sales(engine, len(df))

        print("\n" + "=" * 55)
        print("FACT SALES LOAD COMPLETED SUCCESSFULLY.")
        print("=" * 55)

    finally:
        engine.dispose()


# =========================================================
# 7. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Sales data into Gold."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
