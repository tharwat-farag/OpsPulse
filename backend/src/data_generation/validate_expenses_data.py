
import pandas as pd

from config import RAW_DATA_DIR, START_DATE, END_DATE


def main():

    print("Starting Expenses Data Validation...")

    expenses = pd.read_csv(
        RAW_DATA_DIR / "operating_expenses.csv",
        parse_dates=["expense_date"],
    )

    branches = pd.read_csv(
        RAW_DATA_DIR / "branches.csv"
    )

    # Record count
    assert len(expenses) == 2000, (
        "Incorrect expense record count"
    )

    # Primary key
    assert expenses["expense_id"].is_unique, (
        "Duplicate expense IDs"
    )

    # Required columns
    required_columns = [
        "branch_id",
        "expense_date",
        "expense_category",
        "amount",
        "description",
    ]

    assert expenses[required_columns].notna().all().all(), (
        "Null values found"
    )

    # Foreign key
    valid_branch_ids = set(branches["branch_id"])

    assert set(expenses["branch_id"]).issubset(
        valid_branch_ids
    ), "Unknown branch IDs found"

    # Positive amounts
    assert (expenses["amount"] > 0).all(), (
        "Invalid expense amounts"
    )

    # Valid categories
    valid_categories = {
        "Rent",
        "Electricity",
        "Transportation",
        "Salaries",
        "Maintenance",
    }

    assert set(expenses["expense_category"]).issubset(
        valid_categories
    ), "Invalid expense categories"

    # Date range
    assert expenses["expense_date"].between(
        pd.Timestamp(START_DATE),
        pd.Timestamp(END_DATE),
    ).all(), "Expense dates outside expected period"

    print("Basic Rules Passed!")
    print("Primary Key Validation Passed!")
    print("Foreign Key Validation Passed!")
    print("Amount Validation Passed!")
    print("Category Validation Passed!")
    print("Date Validation Passed!")

    print("\n========== EXPENSES SUMMARY ==========")

    print(f"Total Records: {len(expenses)}")

    print(
        f"Total Operating Expenses: "
        f"{expenses['amount'].sum():,.2f} EGP"
    )

    print("\nExpenses by Category:")

    print(
        expenses.groupby("expense_category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    print("\nExpenses by Branch:")

    print(
        expenses.groupby("branch_id")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    print("\nALL EXPENSES VALIDATIONS PASSED!")


if __name__ == "__main__":
    main()
