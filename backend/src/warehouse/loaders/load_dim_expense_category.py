
import pandas as pd
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
    / "operating_expenses.csv"
)


INSERT_CATEGORY_SQL = text("""
    INSERT INTO gold.dim_expense_category (
        expense_category_name
    )
    VALUES (
        :expense_category_name
    )
    ON CONFLICT (expense_category_name)
    DO NOTHING
""")


def read_expense_categories():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    df = pd.read_csv(SOURCE_FILE)

    if "expense_category" not in df.columns:
        raise ValueError("expense_category column is missing.")

    if df["expense_category"].isna().any():
        raise ValueError("Null expense category found.")

    categories = sorted(
        df["expense_category"].astype(str).str.strip().unique()
    )

    if not categories or any(not category for category in categories):
        raise ValueError("Invalid expense category values.")

    return [
        {"expense_category_name": category}
        for category in categories
    ]


def main():
    print("Starting Expense Category Dimension Load...")

    categories = read_expense_categories()

    print(f"Distinct categories validated: {len(categories)}")

    engine = get_database_engine()

    with engine.begin() as connection:
        result = connection.execute(
            INSERT_CATEGORY_SQL,
            categories
        )

        inserted_count = result.rowcount

    skipped_count = len(categories) - inserted_count

    print("\nExpense Category Load Summary")
    print("-----------------------------")
    print(f"Source categories: {len(categories)}")
    print(f"Inserted:          {inserted_count}")
    print(f"Skipped:           {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
