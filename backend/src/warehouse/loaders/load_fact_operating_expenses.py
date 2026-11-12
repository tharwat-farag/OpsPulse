
from pathlib import Path

import pandas as pd
from sqlalchemy import Date, text

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
    / "operating_expenses.csv"
)

STAGING_TABLE = "stg_operating_expenses"


# ---------------------------------------------------------
# 2. Source validation
# ---------------------------------------------------------

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

    if df.empty:
        raise ValueError("Operating expenses source is empty.")

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
        errors="raise"
    ).dt.date

    # Validate amount.
    if (df["amount"] <= 0).any():
        raise ValueError("Expense amount must be greater than zero.")

    # Validate calendar attributes against expense_date.
    expense_dates = pd.to_datetime(df["expense_date"])

    if not (
        expense_dates.dt.year == df["expense_year"]
    ).all():
        raise ValueError("expense_year validation failed.")

    if not (
        expense_dates.dt.month == df["expense_month"]
    ).all():
        raise ValueError("expense_month validation failed.")

    expected_quarters = (
        "Q" + expense_dates.dt.quarter.astype(str)
    )

    if not (
        expected_quarters == df["expense_quarter"]
    ).all():
        raise ValueError("expense_quarter validation failed.")

    print(f"Source records: {len(df):,}")
    print("Source validation: PASSED")

    return df


# ---------------------------------------------------------
# 3. Database loading
# ---------------------------------------------------------

def load_fact_operating_expenses() -> None:
    df = load_source_data()
    engine = get_database_engine()

    try:
        with engine.begin() as connection:

            # ---------------------------------------------
            # Load source data into staging.
            # ---------------------------------------------

            df.to_sql(
                name=STAGING_TABLE,
                schema="staging",
                con=connection,
                if_exists="replace",
                index=False,
                chunksize=1000,
                method="multi",
                dtype={
                    "expense_date": Date(),
                },
            )

            print("Staging load: COMPLETED")

            # ---------------------------------------------
            # Validate branch and category matching.
            # Branch matching uses SCD Type 2 as-of logic.
            # ---------------------------------------------

            dimension_check = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS source_rows,

                        COUNT(*) FILTER (
                            WHERE branch_match.match_count = 0
                        ) AS missing_branches,

                        COUNT(*) FILTER (
                            WHERE branch_match.match_count > 1
                        ) AS ambiguous_branches,

                        COUNT(*) FILTER (
                            WHERE category.expense_category_key IS NULL
                        ) AS missing_categories

                    FROM staging.stg_operating_expenses s

                    LEFT JOIN LATERAL (
                        SELECT
                            COUNT(*) AS match_count
                        FROM gold.dim_branch b
                        WHERE b.branch_id = s.branch_id
                          AND s.expense_date >= b.valid_from
                          AND s.expense_date < b.valid_to
                    ) branch_match ON TRUE

                    LEFT JOIN gold.dim_expense_category category
                        ON category.expense_category_name =
                           s.expense_category;
                """)
            ).mappings().one()

            print("Dimension validation:")
            print(dict(dimension_check))

            if (
                dimension_check["missing_branches"] != 0
                or dimension_check["ambiguous_branches"] != 0
                or dimension_check["missing_categories"] != 0
            ):
                raise ValueError(
                    "Branch or expense category dimension matching failed."
                )

            print("Dimension matching: PASSED")

            # ---------------------------------------------
            # Insert into Gold Fact.
            # ---------------------------------------------

            insert_result = connection.execute(
                text("""
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
                        ON c.expense_category_name =
                           s.expense_category

                    ON CONFLICT (expense_id) DO NOTHING;
                """)
            )

            print(
                "Records inserted:",
                insert_result.rowcount
            )

            # ---------------------------------------------
            # Reconciliation at expense transaction level.
            # ---------------------------------------------

            reconciliation = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS source_rows,

                        COUNT(f.expense_id) AS matched_fact_rows,

                        COUNT(*) FILTER (
                            WHERE f.expense_id IS NULL
                        ) AS missing_fact_rows,

                        COUNT(*) FILTER (
                            WHERE f.expense_id IS NOT NULL
                              AND (
                                  f.date_key IS DISTINCT FROM d.date_key
                                  OR f.branch_key IS DISTINCT FROM b.branch_key
                                  OR f.expense_category_key IS DISTINCT FROM
                                     c.expense_category_key
                                  OR f.amount IS DISTINCT FROM
                                     s.amount::NUMERIC(14, 2)
                                  OR f.description IS DISTINCT FROM
                                     s.description
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
                        ON c.expense_category_name =
                           s.expense_category;
                """)
            ).mappings().one()

            print("\nReconciliation results:")

            for key, value in reconciliation.items():
                print(f"{key}: {value}")

            # ---------------------------------------------
            # Gold fact totals and uniqueness.
            # ---------------------------------------------

            fact_check = connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS fact_rows,

                        COUNT(DISTINCT expense_id)
                            AS unique_expenses,

                        COALESCE(SUM(amount), 0)
                            AS total_expense_amount

                    FROM gold.fact_operating_expenses;
                """)
            ).mappings().one()

            print("\nGold Fact totals:")
            print(dict(fact_check))

            # ---------------------------------------------
            # Final validation.
            # ---------------------------------------------

            if (
                reconciliation["source_rows"]
                != reconciliation["matched_fact_rows"]
                or reconciliation["missing_fact_rows"] != 0
                or reconciliation["mismatched_rows"] != 0
            ):
                raise ValueError(
                    "Silver-to-Gold row-level reconciliation failed."
                )

            if (
                reconciliation["source_total_amount"]
                != reconciliation["gold_total_amount"]
            ):
                raise ValueError(
                    "Expense amount reconciliation failed."
                )

            if (
                fact_check["fact_rows"]
                != fact_check["unique_expenses"]
            ):
                raise ValueError(
                    "Duplicate expense IDs detected in Gold."
                )

            print("\nSilver-to-Gold reconciliation: PASSED")

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_fact_operating_expenses()
