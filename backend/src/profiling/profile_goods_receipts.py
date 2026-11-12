
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "bronze"
    / BATCH_ID
    / "goods_receipts.csv"
)

df = pd.read_csv(FILE_PATH)

print("=" * 55)
print("GOODS RECEIPTS - DATA PROFILING")
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
print(df.describe().to_string())

print("\n[7] Duplicate Primary Key Check")
if "receipt_id" in df.columns:
    print("Duplicate Receipt IDs:", df["receipt_id"].duplicated().sum())

print("\n[8] Sample Records")
print(df.head(10).to_string(index=False))

print("\nGOODS RECEIPTS PROFILING COMPLETED!")

print("\n[9] Foreign Key Validation")

po_lines_path = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "purchase_order_lines.csv"
)

po_lines = pd.read_csv(po_lines_path)

valid_po_line_ids = set(po_lines["po_line_id"])

print(
    "Invalid PO Line Foreign Keys:",
    (~df["po_line_id"].isin(valid_po_line_ids)).sum()
)

print("\n[10] Quantity Validation")

print(
    "Received Qty <= 0:",
    (df["received_qty"] <= 0).sum()
)

print(
    "Accepted Qty < 0:",
    (df["accepted_qty"] < 0).sum()
)

print(
    "Rejected Qty < 0:",
    (df["rejected_qty"] < 0).sum()
)

print(
    "Received != Accepted + Rejected:",
    (
        df["received_qty"]
        != df["accepted_qty"] + df["rejected_qty"]
    ).sum()
)

print("\n[11] Date Validation")

df["received_date_parsed"] = pd.to_datetime(
    df["received_date"],
    errors="coerce"
)

print(
    "Invalid Dates:",
    df["received_date_parsed"].isna().sum()
)

print(
    "Dates Outside 2025:",
    (
        (df["received_date_parsed"] < "2025-01-01")
        | (df["received_date_parsed"] > "2025-12-31")
    ).sum()
)

print("\n[12] Received Quantity vs Ordered Quantity")

merged = df.merge(
    po_lines[["po_line_id", "ordered_qty"]],
    on="po_line_id",
    how="left"
)

received_totals = (
    merged.groupby("po_line_id")["received_qty"]
    .sum()
    .reset_index()
)

received_totals = received_totals.merge(
    po_lines[["po_line_id", "ordered_qty"]],
    on="po_line_id",
    how="left"
)

received_totals["exceeds_ordered_qty"] = (
    received_totals["received_qty"]
    > received_totals["ordered_qty"]
)

print(
    "PO Lines Exceeding Ordered Quantity:",
    received_totals["exceeds_ordered_qty"].sum()
)

print(
    "Maximum Received / Ordered Ratio:",
    round(
        (
            received_totals["received_qty"]
            / received_totals["ordered_qty"]
        ).max(),
        3
    )
)

print("\nBusiness Rule Validation Completed!")

print("\n[13] Investigate Receipts Outside 2025")

outside_2025 = df.loc[
    (df["received_date_parsed"] < "2025-01-01")
    | (df["received_date_parsed"] > "2025-12-31")
].copy()

investigation = outside_2025.merge(
    po_lines[
        ["po_line_id", "po_id", "ordered_qty"]
    ],
    on="po_line_id",
    how="left"
)

investigation = investigation.merge(
    pd.read_csv(
        PROJECT_ROOT
        / "data"
        / "silver"
        / BATCH_ID
        / "purchase_orders.csv"
    )[["po_id", "order_date", "expected_delivery_date", "status"]],
    on="po_id",
    how="left"
)

print(
    investigation[
        [
            "receipt_id",
            "po_line_id",
            "received_date",
            "received_qty",
            "ordered_qty",
            "po_id",
            "order_date",
            "expected_delivery_date",
            "status",
        ]
    ].to_string(index=False)
)
