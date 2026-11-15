
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import Date, text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STAGING_TABLE = "stg_operating_expenses"
CHUNK_SIZE = 1000

REQUIRED_COLUMNS = [
    "expense_id",
    "branch_id",
    "expense_date",
    "expense_category",
    "amount",
    "description",
    "expense_year",
    "expense_month",
    "expense_quarter",
]


# =========================================================
# 1. READ AND VALIDATE SOURCE DATA
# =========================================================

def read_source_data(batch_id: str) -> pd.DataFrame:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "operating_expenses.csv"
    )

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

    if df.empty:
        raise ValueError(
            "Operating expenses source is empty."
        )

    # Description is optional; other fields are mandatory.
    mandatory_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column != "description"
    ]

    null_columns = [
        column
        for column in mandatory_columns
        if df[column].isnull().any()
    ]

    if null_columns:
        raise ValueError(
            f"Null values found in mandatory columns: {null_columns}"
        )

    # Expense ID must be unique.
    duplicate_ids = df["expense_id"].duplicated().sum()

    if duplicate_ids:
        raise ValueError(
            f"Duplicate expense_id values found: {duplicate_ids}"
        )

    # Parse expense date.
    df["expense_date"] = pd.to_datetime(
        df["expense_date"],
        errors="raise",
    ).dt.date

    # Validate amount.
    if (df["amount"] <= 0).any():
        raise ValueError(
            "Expense amount must be greater than zero."
        )

    # Validate calendar attributes.
    expense_dates = pd.to_datetime(df["expense_date"])

    if not (
        expense_dates.dt.year == df["expense_year"]
    ).all():
        raise ValueError(
            "expense_year validation failed."
        )

    if not (
        expense_dates.dt.month == df["expense_month"]
    ).all():
        raise ValueError(
            "expense_month validation failed."
        )

    expected_quarters = (
        "Q" + expense_dates.dt.quarter.astype(str)
    )

    if not (
        expected_quarters == df["expense_quarter"]
    ).all():
        raise ValueError(
            "expense_quarter validation failed."
        )

    print(f"Source records: {len(df):,}")
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
            dtype={
                "expense_date": Date(),
            },
        )

    print("Staging load: COMPLETED")


# =========================================================
# 3. VALIDATE DIMENSION MATCHES
# =========================================================

def validate_dimension_matches(engine) -> None:

    dimension_sql = text("""
        SELECT
            COUNT(*) AS source_rows,

            COUNT(*) FILTER (
                WHERE branch_match.match_count = 0
            ) AS missing_branches,

            COUNT(*) FILTER (
                WHERE branch_match.match_count > 1
            ) AS ambiguous_branches,

            COUNT(*) FILTER (
                WHERE category_match.match_count = 0
            ) AS missing_categories,

            COUNT(*) FILTER (
                WHERE category_match.match_count > 1
            ) AS ambiguous_categories

        FROM staging.stg_operating_expenses s

        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS match_count
            FROM gold.dim_branch b
            WHERE b.branch_id = s.branch_id
              AND s.expense_date >= b.valid_from
              AND s.expense_date < b.valid_to
        ) branch_match ON TRUE

        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS match_count
            FROM gold.dim_expense_category c
            WHERE c.expense_category_name = s.expense_category
        ) category_match ON TRUE;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            dimension_sql
        ).mappings().one()

    print("\nDimension validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    invalid_total = (
        result["missing_branches"]
        + result["ambiguous_branches"]
        + result["missing_categories"]
        + result["ambiguous_categories"]
    )

    if invalid_total > 0:
        raise ValueError(
            "Branch or expense category dimension matching failed."
        )

    print("Dimension matching: PASSED")


# =========================================================
# 4. LOAD FACT OPERATING EXPENSES
# =========================================================

def load_fact_operating_expenses(engine) -> None:

    insert_sql = text("""
        INSERT INTO gold.fact_operating_expenses (
            expense_id,
            date_key,
            branch_key,
            expense_category_key,
            amount,
            description
        )

        SELECT
            s.expense_id,
            d.date_key,
            b.branch_key,
            c.expense_category_key,
            s.amount::NUMERIC(14, 2),
            s.description

        FROM staging.stg_operating_expenses s

        JOIN gold.dim_date d
            ON d.full_date = s.expense_date

        JOIN gold.dim_branch b
            ON b.branch_id = s.branch_id
           AND s.expense_date >= b.valid_from
           AND s.expense_date < b.valid_to

        JOIN gold.dim_expense_category c
            ON c.expense_category_name = s.expense_category

        ON CONFLICT (expense_id) DO NOTHING;
    """)

    with engine.begin() as connection:

        before_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_operating_expenses
            """)
        ).scalar_one()

        connection.execute(insert_sql)

        after_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_operating_expenses
            """)
        ).scalar_one()

    inserted = after_count - before_count

    print("\nFact Operating Expenses load:")
    print(f"Records inserted: {inserted:,}")
    print(f"Total records in Gold: {after_count:,}")


# =========================================================
# 5. RECONCILIATION
# =========================================================

def reconcile_operating_expenses(
    engine,
    source_count: int,
) -> None:

    reconciliation_sql = text("""
        SELECT

            COUNT(*) AS source_rows,

            COUNT(f.expense_id) AS matched_fact_rows,

            COUNT(DISTINCT s.expense_id)
                AS unique_source_expenses,

            COUNT(DISTINCT f.expense_id)
                AS unique_fact_expenses,

            COUNT(*) FILTER (
                WHERE f.expense_id IS NULL
            ) AS missing_fact_rows,

            COUNT(*) FILTER (
                WHERE
                    f.expense_id IS NOT NULL
                    AND (
                        f.date_key IS DISTINCT FROM d.date_key

                        OR f.branch_key IS DISTINCT FROM b.branch_key

                        OR f.expense_category_key
                            IS DISTINCT FROM c.expense_category_key

                        OR f.amount IS DISTINCT FROM
                            s.amount::NUMERIC(14, 2)

                        OR f.description IS DISTINCT FROM s.description
                    )
            ) AS mismatched_rows,

            COALESCE(
                SUM(s.amount::NUMERIC(14, 2)), 0
            ) AS source_total_amount,

            COALESCE(
                SUM(f.amount), 0
            ) AS gold_total_amount

        FROM staging.stg_operating_expenses s

        LEFT JOIN gold.fact_operating_expenses f
            ON f.expense_id = s.expense_id

        LEFT JOIN gold.dim_date d
            ON d.full_date = s.expense_date

        LEFT JOIN gold.dim_branch b
            ON b.branch_id = s.branch_id
           AND s.expense_date >= b.valid_from
           AND s.expense_date < b.valid_to

        LEFT JOIN gold.dim_expense_category c
            ON c.expense_category_name = s.expense_category;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value}")

    # Source row count.
    if result["source_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: source row count mismatch."
        )

    # Source uniqueness.
    if result["unique_source_expenses"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate source expense IDs."
        )

    # Gold matching.
    if result["matched_fact_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: missing or duplicate fact matches."
        )

    if result["unique_fact_expenses"] != source_count:
        raise ValueError(
            "Reconciliation failed: missing or duplicate fact expense IDs."
        )

    if result["missing_fact_rows"] != 0:
        raise ValueError(
            "Reconciliation failed: missing fact rows."
        )

    if result["mismatched_rows"] != 0:
        raise ValueError(
            "Reconciliation failed: source and fact values do not match."
        )

    # Financial reconciliation.
    if (
        result["source_total_amount"]
        != result["gold_total_amount"]
    ):
        raise ValueError(
            "Expense amount reconciliation failed."
        )

    # Global Gold uniqueness check.
    fact_check_sql = text("""
        SELECT
            COUNT(*) AS fact_rows,

            COUNT(DISTINCT expense_id) AS unique_expenses,

            COALESCE(SUM(amount), 0) AS total_expense_amount

        FROM gold.fact_operating_expenses;
    """)

    with engine.connect() as connection:

        fact_check = connection.execute(
            fact_check_sql
        ).mappings().one()

    print("\nGold Fact totals:")

    for key, value in fact_check.items():
        print(f"{key}: {value}")

    if fact_check["fact_rows"] != fact_check["unique_expenses"]:
        raise ValueError(
            "Duplicate expense IDs detected in Gold."
        )

    print("\nSilver-to-Gold reconciliation: PASSED")


# =========================================================
# 6. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError(
            "A valid batch_id is required."
        )

    print("=" * 60)
    print("OPSPULSE - FACT OPERATING EXPENSES LOADER")
    print(f"Batch ID: {batch_id}")
    print("=" * 60)

    engine = get_database_engine()

    try:

        # Step 1: Read and validate Silver data.
        df = read_source_data(batch_id)

        # Step 2: Load Staging.
        load_to_staging(engine, df)

        # Step 3: Validate dimension matching.
        validate_dimension_matches(engine)

        # Step 4: Load Gold Fact.
        load_fact_operating_expenses(engine)

        # Step 5: Reconcile Silver and Gold.
        reconcile_operating_expenses(
            engine,
            len(df),
        )

        print("\n" + "=" * 60)
        print("FACT OPERATING EXPENSES LOAD COMPLETED SUCCESSFULLY.")
        print("=" * 60)

    finally:
        engine.dispose()


# =========================================================
# 7. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Operating Expenses data into Gold."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
