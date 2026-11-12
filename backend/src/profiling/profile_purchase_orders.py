
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / BATCH_ID
    / "purchase_orders.csv"
)

print("=" * 55)
print("PURCHASE ORDERS - DATA PROFILING")
print("=" * 55)

df = pd.read_csv(FILE_PATH)

print("\n[1] Dataset Overview")
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print("\nColumn Names:")
print(df.columns.tolist())

print("\n[2] Data Types")
print(df.dtypes)

print("\n[3] Missing Values")
print(df.isnull().sum())

print("\n[4] Duplicate Records")
print(f"Duplicate Rows: {df.duplicated().sum()}")

print("\n[5] Duplicate Primary Keys")
if "po_id" in df.columns:
    print(df["po_id"].duplicated().sum())

print("\n[6] Unique Values")
for column in df.columns:
    print(f"\n{column}:")
    print(f"Unique Values: {df[column].nunique()}")

    if df[column].nunique() <= 20:
        print(df[column].value_counts(dropna=False))

print("\n[7] Sample Records")
print(df.head(10).to_string(index=False))

print("\n[8] Numeric Profiling")
print(df.describe(include="all").to_string())

print("\nPURCHASE ORDERS PROFILING COMPLETED!")

print("\n[9] Business Rule Validation")

# Date validation
df["order_date_parsed"] = pd.to_datetime(
    df["order_date"], errors="coerce"
)

df["expected_date_parsed"] = pd.to_datetime(
    df["expected_delivery_date"], errors="coerce"
)

print(
    "Invalid Order Dates:",
    df["order_date_parsed"].isna().sum()
)

print(
    "Invalid Expected Delivery Dates:",
    df["expected_date_parsed"].isna().sum()
)

# Expected date must not precede order date
invalid_date_sequence = (
    df["expected_date_parsed"] < df["order_date_parsed"]
)

print(
    "Expected Date Before Order Date:",
    invalid_date_sequence.sum()
)

# Date range
print(
    "Order Dates Outside 2025:",
    (
        (df["order_date_parsed"] < "2025-01-01")
        | (df["order_date_parsed"] > "2025-12-31")
    ).sum()
)

# Supplier foreign key validation
suppliers_path = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "suppliers.csv"
)

suppliers = pd.read_csv(suppliers_path)

valid_supplier_ids = set(suppliers["supplier_id"])

invalid_suppliers = ~df["supplier_id"].isin(valid_supplier_ids)

print(
    "Invalid Supplier Foreign Keys:",
    invalid_suppliers.sum()
)

print("\nBusiness Rule Validation Completed!")
