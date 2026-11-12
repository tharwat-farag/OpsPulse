
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "sales.csv"
)

STAGING_TABLE = "stg_sales"

# PostgreSQL parameter limit safety:
# 1000 rows x 15 columns = 15000 parameters per batch.
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

def read_sales_data() -> pd.DataFrame:

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Silver sales file not found: {SOURCE_FILE}"
        )

    df = pd.read_csv(
        SOURCE_FILE,
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
    df: pd.DataFrame
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
    source_count: int
) -> None:

    reconciliation_sql = text("""
        SELECT
            COUNT(*) AS fact_rows,

            COUNT(DISTINCT f.sales_line_id)
                AS unique_sales_lines,

            SUM(f.gross_amount) AS gross_amount,

            SUM(f.discount_amount) AS discount_amount,

            SUM(f.net_revenue) AS net_revenue,

            SUM(f.total_cost) AS total_cost,

            SUM(f.gross_profit) AS gross_profit

        FROM gold.fact_sales f

        INNER JOIN staging.stg_sales s
            ON s.sales_line_id = f.sales_line_id;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value}")

    if result["fact_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: "
            "Fact Sales count does not match Silver."
        )

    if result["unique_sales_lines"] != source_count:
        raise ValueError(
            "Reconciliation failed: "
            "Duplicate or missing sales lines."
        )

    print("Silver-to-Gold reconciliation: PASSED")


# =========================================================
# 6. MAIN EXECUTION
# =========================================================

def main() -> None:

    print("=" * 55)
    print("OPSPULSE - FACT SALES LOADER")
    print("=" * 55)

    engine = get_database_engine()

    try:

        # Step 1
        df = read_sales_data()

        # Step 2
        load_to_staging(engine, df)

        # Step 3
        validate_dimension_matches(engine)

        # Step 4
        load_fact_sales(engine)

        # Step 5
        reconcile_sales(engine, len(df))

        print("\n" + "=" * 55)
        print("FACT SALES LOAD COMPLETED SUCCESSFULLY.")
        print("=" * 55)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
