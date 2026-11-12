
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / BATCH_ID
    / "purchase_order_lines.csv"
)

df = pd.read_csv(FILE_PATH)

print("=" * 55)
print("PURCHASE ORDER LINES - DATA PROFILING")
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
    print("Unique:", df[column].nunique())

    if df[column].nunique() <= 20:
        print(df[column].value_counts(dropna=False))

print("\n[6] Numeric Profiling")
print(df.describe().to_string())

print("\n[7] Primary Key Check")
if "po_line_id" in df.columns:
    print("Duplicate PO Line IDs:", df["po_line_id"].duplicated().sum())

print("\n[8] Sample Records")
print(df.head(10).to_string(index=False))

print("\nPURCHASE ORDER LINES PROFILING COMPLETED!")

print("\n[9] Foreign Key Validation")

po_path = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "purchase_orders.csv"
)

products_path = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "products.csv"
)

purchase_orders = pd.read_csv(po_path)
products = pd.read_csv(products_path)

valid_po_ids = set(purchase_orders["po_id"])
valid_product_ids = set(products["product_id"])

print(
    "Invalid PO Foreign Keys:",
    (~df["po_id"].isin(valid_po_ids)).sum()
)

print(
    "Invalid Product Foreign Keys:",
    (~df["product_id"].isin(valid_product_ids)).sum()
)

print("\n[10] Numeric Business Validation")

print("Non-positive Ordered Quantity:", (df["ordered_qty"] <= 0).sum())
print("Non-positive Unit Cost:", (df["unit_cost"] <= 0).sum())

print(
    "Non-integer Ordered Quantity:",
    (df["ordered_qty"] % 1 != 0).sum()
)

print("\n[11] Purchase Order Line Distribution")

print("Lines per PO:")
print(df.groupby("po_id").size().describe())

print("\n[12] Purchase Order Line Amount")

df["line_total"] = df["ordered_qty"] * df["unit_cost"]

print(df["line_total"].describe())

print("\nAdditional Profiling Completed!")
