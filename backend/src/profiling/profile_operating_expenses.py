
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / BATCH_ID
    / "operating_expenses.csv"
)

df = pd.read_csv(FILE_PATH)

print("=" * 55)
print("OPERATING EXPENSES - DATA PROFILING")
print("=" * 55)

print("\n[1] Dataset Overview")
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(df.columns.tolist())

print("\n[2] Data Types")
print(df.dtypes)

print("\n[3] Missing Values")
print(df.isnull().sum())

print("\n[4] Duplicate Records")
print(df.duplicated().sum())

print("\n[5] Unique Values")

for column in df.columns:
    print(f"\n{column}:")
    print("Unique Values:", df[column].nunique())

    if df[column].nunique() <= 20:
        print(df[column].value_counts(dropna=False))

print("\n[6] Numeric Profiling")
print(df.describe(include="all").to_string())

print("\n[7] Duplicate Primary Key Check")

if "expense_id" in df.columns:
    print(
        "Duplicate Expense IDs:",
        df["expense_id"].duplicated().sum()
    )

print("\n[8] Sample Records")
print(df.head(10).to_string(index=False))

print("\nOPERATING EXPENSES PROFILING COMPLETED!")

print("\n[9] Foreign Key Validation")

branches_path = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "branches.csv"
)

branches = pd.read_csv(branches_path)

valid_branch_ids = set(branches["branch_id"])

print(
    "Invalid Branch Foreign Keys:",
    (~df["branch_id"].isin(valid_branch_ids)).sum()
)

print("\n[10] Amount Validation")

print("Non-positive Amounts:", (df["amount"] <= 0).sum())

print("\n[11] Date Validation")

df["expense_date_parsed"] = pd.to_datetime(
    df["expense_date"],
    errors="coerce"
)

print(
    "Invalid Dates:",
    df["expense_date_parsed"].isna().sum()
)

print(
    "Dates Outside 2025:",
    (
        (df["expense_date_parsed"] < "2025-01-01")
        | (df["expense_date_parsed"] > "2025-12-31")
    ).sum()
)

print("\n[12] Expense Category Validation")

allowed_categories = {
    "Transportation",
    "Rent",
    "Salaries",
    "Maintenance",
    "Electricity",
}

print(
    "Invalid Categories:",
    (~df["expense_category"].isin(allowed_categories)).sum()
)

print("\n[13] Expense Summary by Category")

print(
    df.groupby("expense_category")["amount"]
    .agg(["count", "sum", "mean"])
    .round(2)
    .to_string()
)

print("\nAdditional Profiling Completed!")
