
import random
import pandas as pd

from datetime import timedelta

from config import (
    RANDOM_SEED,
    START_DATE,
    END_DATE,
    RAW_DATA_DIR,
)

random.seed(RANDOM_SEED)


EXPENSE_CATEGORIES = {
    "Rent": {
        "amount_range": (15000, 50000),
        "descriptions": [
            "Monthly branch rent",
            "Office rental payment",
            "Warehouse rental payment",
        ],
    },

    "Electricity": {
        "amount_range": (2000, 12000),
        "descriptions": [
            "Monthly electricity bill",
            "Warehouse electricity consumption",
            "Branch electricity payment",
        ],
    },

    "Transportation": {
        "amount_range": (1000, 15000),
        "descriptions": [
            "Product transportation",
            "Delivery vehicle fuel",
            "Distribution transportation cost",
        ],
    },

    "Salaries": {
        "amount_range": (10000, 80000),
        "descriptions": [
            "Monthly employee salaries",
            "Branch staff payroll",
            "Operations team salaries",
        ],
    },

    "Maintenance": {
        "amount_range": (500, 10000),
        "descriptions": [
            "Equipment maintenance",
            "Warehouse maintenance",
            "Branch facility repairs",
        ],
    },
}


def load_branches():

    return pd.read_csv(
        RAW_DATA_DIR / "branches.csv"
    )


def generate_expenses(branches):

    expenses = []

    branch_ids = branches["branch_id"].tolist()

    total_days = (END_DATE - START_DATE).days

    for i in range(1, 2001):

        branch_id = random.choice(branch_ids)

        expense_category = random.choice(
            list(EXPENSE_CATEGORIES.keys())
        )

        category_config = EXPENSE_CATEGORIES[
            expense_category
        ]

        min_amount, max_amount = (
            category_config["amount_range"]
        )

        amount = round(
            random.uniform(min_amount, max_amount),
            2,
        )

        expense_date = START_DATE + timedelta(
            days=random.randint(0, total_days)
        )

        description = random.choice(
            category_config["descriptions"]
        )

        expenses.append({
            "expense_id": f"EX{i:05d}",
            "branch_id": branch_id,
            "expense_date": expense_date,
            "expense_category": expense_category,
            "amount": amount,
            "description": description,
        })

    return pd.DataFrame(expenses)


def main():

    print("Starting Operating Expenses Generation...")

    branches = load_branches()

    expenses_df = generate_expenses(branches)

    output_path = RAW_DATA_DIR / "operating_expenses.csv"

    expenses_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nSaved: {output_path}")

    print(f"Total Records: {len(expenses_df)}")

    print("\nExpenses by Category:")

    print(
        expenses_df["expense_category"].value_counts()
    )

    print("\nExpenses by Branch:")

    print(
        expenses_df.groupby("branch_id")["amount"].sum()
    )

    print("\nTotal Operating Expenses:")

    print(
        f"{expenses_df['amount'].sum():,.2f} EGP"
    )

    print("\nExpenses Preview:")

    print(expenses_df.head())

    print("\nOperating Expenses Generation Completed!")


if __name__ == "__main__":
    main()
