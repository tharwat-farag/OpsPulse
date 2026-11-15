
import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]


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


def read_expense_categories(batch_id: str) -> list[dict]:
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must not be empty.")

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "operating_expenses.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    df = pd.read_csv(source_file)

    if "expense_category" not in df.columns:
        raise ValueError("expense_category column is missing.")

    if df["expense_category"].isna().any():
        raise ValueError("Null expense category found.")

    normalized_categories = (
        df["expense_category"]
        .astype(str)
        .str.strip()
    )

    if normalized_categories.empty:
        raise ValueError("No expense category records found.")

    if normalized_categories.eq("").any():
        raise ValueError("Empty expense category value found.")

    categories = sorted(normalized_categories.unique().tolist())

    return [
        {"expense_category_name": category}
        for category in categories
    ]


def main(batch_id: str) -> None:
    print("Starting Expense Category Dimension Load...")
    print(f"Batch ID: {batch_id}")

    categories = read_expense_categories(batch_id)

    print(f"Distinct categories validated: {len(categories)}")

    engine = get_database_engine()

    try:
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

    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Load Expense Category Dimension from a Silver batch."
        )
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Silver batch ID to load."
    )

    args = parser.parse_args()
    main(args.batch_id)
