
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SILVER_DIR = PROJECT_ROOT / "data" / "silver" / BATCH_ID

DATASETS = [
    "products",
    "customers",
    "branches",
    "suppliers",
    "warehouses",
    "product_suppliers",
    "sales",
    "inventory",
    "purchase_orders",
    "purchase_order_lines",
    "goods_receipts",
    "operating_expenses",
]

print("=" * 75)
print("OPSPULSE - SILVER LAYER FINAL AUDIT")
print("=" * 75)
print(f"Batch: {BATCH_ID}\n")

results = []

for dataset in DATASETS:
    silver_file = SILVER_DIR / f"{dataset}.csv"
    quarantine_file = SILVER_DIR / f"{dataset}_quarantine.csv"
    manifest_file = (
        SILVER_DIR / f"{dataset}_transformation_manifest.json"
    )

    missing = []

    if not silver_file.exists():
        missing.append("Silver file")

    if not quarantine_file.exists():
        missing.append("Quarantine file")

    if not manifest_file.exists():
        missing.append("Transformation manifest")

    if missing:
        results.append({
            "Dataset": dataset,
            "Silver Rows": 0,
            "Quarantine Rows": 0,
            "Status": "MISSING: " + ", ".join(missing),
        })
        continue

    silver_df = pd.read_csv(silver_file)
    quarantine_df = pd.read_csv(quarantine_file)

    results.append({
        "Dataset": dataset,
        "Silver Rows": len(silver_df),
        "Quarantine Rows": len(quarantine_df),
        "Status": "OK",
    })

audit_df = pd.DataFrame(results)

print(audit_df.to_string(index=False))

print("\n" + "=" * 75)

all_files_exist = (audit_df["Status"] == "OK").all()

total_silver = audit_df["Silver Rows"].sum()
total_quarantine = audit_df["Quarantine Rows"].sum()

print(f"Total Silver Records: {total_silver:,}")
print(f"Total Quarantine Records: {total_quarantine:,}")
print(f"Datasets Audited: {len(DATASETS)}")
print(f"All Required Files Exist: {all_files_exist}")

if all_files_exist:
    print("\nSILVER LAYER FILE AUDIT PASSED!")
else:
    print("\nSILVER LAYER FILE AUDIT FAILED!")
