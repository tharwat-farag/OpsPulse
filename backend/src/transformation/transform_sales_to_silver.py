
import json

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ==================================================
# 1. PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

VALID_CHANNELS = {
    "In-Store",
    "Phone",
    "Online",
}

REQUIRED_COLUMNS = [
    "sales_line_id",
    "invoice_id",
    "sale_date",
    "product_id",
    "customer_id",
    "branch_id",
    "quantity",
    "unit_price",
    "unit_cost",
    "discount_amount",
    "sales_channel",
]


# ==================================================
# 2. FIND LATEST BRONZE BATCH
# ==================================================

def find_latest_batch():

    batches = sorted(
        [
            path
            for path in BRONZE_DIR.glob("batch_*")
            if (path / "ingestion_manifest.json").exists()
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not batches:
        raise FileNotFoundError(
            "No Bronze ingestion batch found."
        )

    return batches[0]


# ==================================================
# 3. LOAD REFERENCE DATA
# ==================================================

def load_reference_data(batch_dir):

    print("\nLoading reference datasets...")

    products = pd.read_csv(
        batch_dir / "products.csv"
    )

    customers = pd.read_csv(
        batch_dir / "customers.csv"
    )

    branches = pd.read_csv(
        batch_dir / "branches.csv"
    )

    return products, customers, branches


# ==================================================
# 4. LOAD SALES DATA
# ==================================================

def load_sales(batch_dir):

    print("\nLoading Bronze Sales...")

    sales = pd.read_csv(
        batch_dir / "sales.csv"
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in sales.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return sales


# ==================================================
# 5. STANDARDIZE DATA TYPES AND TEXT
# ==================================================

def standardize_sales(sales):

    print("\nStandardizing data...")

    sales = sales.copy()

    # Standardize text columns.
    text_columns = [
        "sales_line_id",
        "invoice_id",
        "product_id",
        "customer_id",
        "branch_id",
        "sales_channel",
    ]

    for column in text_columns:

        sales[column] = (
            sales[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Standardize date.
    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

    # Standardize numeric columns.
    numeric_columns = [
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
    ]

    for column in numeric_columns:

        sales[column] = pd.to_numeric(
            sales[column],
            errors="coerce",
        )

    return sales


# ==================================================
# 6. VALIDATE DATA QUALITY
# ==================================================

def validate_sales(
    sales,
    products,
    customers,
    branches,
):

    print("\nRunning mandatory data quality checks...")

    sales = sales.copy()

    # Each row starts with no rejection reason.
    reasons = pd.Series(
        "",
        index=sales.index,
        dtype="string",
    )

    def add_reason(mask, reason):

        mask = mask.fillna(True)

        reasons.loc[mask] = reasons.loc[mask].apply(
            lambda current: (
                f"{current}; {reason}"
                if current
                else reason
            )
        )

    # ----------------------------------------------
    # Required fields
    # ----------------------------------------------

    required_fields = [
        "sales_line_id",
        "invoice_id",
        "sale_date",
        "product_id",
        "customer_id",
        "branch_id",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
        "sales_channel",
    ]

    for column in required_fields:

        add_reason(
            sales[column].isna(),
            f"MISSING_{column.upper()}",
        )

    # ----------------------------------------------
    # Primary key
    # ----------------------------------------------

    duplicate_ids = sales[
        "sales_line_id"
    ].duplicated(keep=False)

    add_reason(
        duplicate_ids,
        "DUPLICATE_SALES_LINE_ID",
    )

    # ----------------------------------------------
    # Numeric business rules
    # ----------------------------------------------

    add_reason(
        sales["quantity"].notna()
        & (sales["quantity"] <= 0),
        "INVALID_QUANTITY",
    )

    add_reason(
        sales["unit_price"].notna()
        & (sales["unit_price"] <= 0),
        "INVALID_UNIT_PRICE",
    )

    add_reason(
        sales["unit_cost"].notna()
        & (sales["unit_cost"] <= 0),
        "INVALID_UNIT_COST",
    )

    add_reason(
        sales["discount_amount"].notna()
        & (sales["discount_amount"] < 0),
        "NEGATIVE_DISCOUNT",
    )

    # ----------------------------------------------
    # Discount cannot exceed gross amount
    # ----------------------------------------------

    gross_amount = (
        sales["quantity"] * sales["unit_price"]
    )

    add_reason(
        gross_amount.notna()
        & sales["discount_amount"].notna()
        & (
            sales["discount_amount"] > gross_amount
        ),
        "DISCOUNT_EXCEEDS_GROSS_AMOUNT",
    )

    # ----------------------------------------------
    # Date validation
    # ----------------------------------------------

    add_reason(
        sales["sale_date"].notna()
        & (
            (sales["sale_date"] < pd.Timestamp("2025-01-01"))
            | (sales["sale_date"] > pd.Timestamp("2025-12-31"))
        ),
        "DATE_OUTSIDE_EXPECTED_PERIOD",
    )

    # ----------------------------------------------
    # Sales channel validation
    # ----------------------------------------------

    add_reason(
        sales["sales_channel"].notna()
        & ~sales["sales_channel"].isin(VALID_CHANNELS),
        "INVALID_SALES_CHANNEL",
    )

    # ----------------------------------------------
    # Foreign key validation
    # ----------------------------------------------

    valid_products = set(products["product_id"])
    valid_customers = set(customers["customer_id"])
    valid_branches = set(branches["branch_id"])

    add_reason(
        sales["product_id"].notna()
        & ~sales["product_id"].isin(valid_products),
        "INVALID_PRODUCT_ID",
    )

    add_reason(
        sales["customer_id"].notna()
        & ~sales["customer_id"].isin(valid_customers),
        "INVALID_CUSTOMER_ID",
    )

    add_reason(
        sales["branch_id"].notna()
        & ~sales["branch_id"].isin(valid_branches),
        "INVALID_BRANCH_ID",
    )

    # ----------------------------------------------
    # Separate valid and rejected records
    # ----------------------------------------------

    sales["quarantine_reason"] = reasons

    quarantine_mask = reasons.ne("")

    valid_sales = sales.loc[
        ~quarantine_mask
    ].copy()

    quarantined_sales = sales.loc[
        quarantine_mask
    ].copy()

    return valid_sales, quarantined_sales


# ==================================================
# 7. APPLY BUSINESS TRANSFORMATIONS
# ==================================================

def apply_business_transformations(sales):

    print("\nApplying business transformations...")

    sales = sales.copy()

    # Gross sales amount before discount.
    sales["gross_amount"] = (
        sales["quantity"] * sales["unit_price"]
    )

    # Revenue after discount.
    sales["net_revenue"] = (
        sales["gross_amount"]
        - sales["discount_amount"]
    )

    # Total product cost.
    sales["total_cost"] = (
        sales["quantity"] * sales["unit_cost"]
    )

    # Gross profit after discount and product cost.
    sales["gross_profit"] = (
        sales["net_revenue"]
        - sales["total_cost"]
    )

    # Discount percentage.
    sales["discount_rate"] = (
        sales["discount_amount"]
        / sales["gross_amount"]
    )

    # Business exception flag.
    sales["is_loss_making"] = (
        sales["gross_profit"] < 0
    )

    # Remove quarantine helper column.
    sales = sales.drop(
        columns=["quarantine_reason"],
        errors="ignore",
    )

    # Put important columns together.
    ordered_columns = [
        "sales_line_id",
        "invoice_id",
        "sale_date",
        "product_id",
        "customer_id",
        "branch_id",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
        "gross_amount",
        "net_revenue",
        "total_cost",
        "gross_profit",
        "discount_rate",
        "is_loss_making",
        "sales_channel",
    ]

    return sales[ordered_columns]


# ==================================================
# 8. SAVE SILVER AND QUARANTINE
# ==================================================

def save_outputs(
    silver_sales,
    quarantined_sales,
    batch_dir,
    source_batch_id,
):

    silver_batch_dir = (
        SILVER_DIR / source_batch_id
    )

    silver_batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    silver_path = (
        silver_batch_dir / "sales.csv"
    )

    quarantine_path = (
        silver_batch_dir / "sales_quarantine.csv"
    )

    # Save transformed Silver data.
    silver_sales.to_csv(
        silver_path,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    # Save rejected records separately.
    quarantined_sales.to_csv(
        quarantine_path,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    # Build transformation manifest.
    loss_count = int(
        silver_sales["is_loss_making"].sum()
    )

    manifest = {
        "source_batch_id": source_batch_id,
        "transformation_timestamp_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "source_layer": "Bronze",
        "target_layer": "Silver",
        "source_file": "sales.csv",
        "output_file": "sales.csv",
        "quarantine_file": "sales_quarantine.csv",
        "input_records": (
            len(silver_sales) + len(quarantined_sales)
        ),
        "silver_records": len(silver_sales),
        "quarantined_records": len(quarantined_sales),
        "loss_making_records": loss_count,
        "status": "SUCCESS",
    }

    manifest_path = (
        silver_batch_dir / "sales_transformation_manifest.json"
    )

    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return silver_batch_dir, manifest


# ==================================================
# 9. SILVER VALIDATION
# ==================================================

def validate_silver(
    silver_sales,
    quarantined_sales,
    original_count,
):

    print("\n========== SILVER VALIDATION ==========")

    assert (
        len(silver_sales) + len(quarantined_sales)
        == original_count
    ), "Record reconciliation failed"

    assert silver_sales["sales_line_id"].is_unique, (
        "Duplicate Sales Line IDs found in Silver"
    )

    assert silver_sales.isnull().sum().sum() == 0, (
        "Missing values found in Silver"
    )

    assert (
        silver_sales["gross_profit"].notna().all()
    ), "Invalid gross profit calculations"

    assert (
        silver_sales["is_loss_making"]
        == (silver_sales["gross_profit"] < 0)
    ).all(), "Loss flag does not match gross profit"

    assert (
        silver_sales["discount_amount"]
        <= silver_sales["gross_amount"]
    ).all(), "Invalid discounts found in Silver"

    print("Record Reconciliation: PASSED")
    print("Primary Key Validation: PASSED")
    print("Missing Values Validation: PASSED")
    print("Financial Calculations: PASSED")
    print("Loss Flag Validation: PASSED")
    print("Discount Validation: PASSED")


# ==================================================
# 10. PRINT SUMMARY
# ==================================================

def print_summary(
    silver_sales,
    quarantined_sales,
    manifest,
    output_dir,
):

    print("\n" + "=" * 55)
    print("             SILVER TRANSFORMATION SUMMARY")
    print("=" * 55)

    print(
        f"Input Records: {manifest['input_records']:,}"
    )

    print(
        f"Silver Records: {len(silver_sales):,}"
    )

    print(
        f"Quarantined Records: {len(quarantined_sales):,}"
    )

    print(
        f"Loss-Making Records: "
        f"{manifest['loss_making_records']:,}"
    )

    print(
        f"Gross Revenue: "
        f"{silver_sales['gross_amount'].sum():,.2f} EGP"
    )

    print(
        f"Net Revenue: "
        f"{silver_sales['net_revenue'].sum():,.2f} EGP"
    )

    print(
        f"Total Cost: "
        f"{silver_sales['total_cost'].sum():,.2f} EGP"
    )

    print(
        f"Gross Profit: "
        f"{silver_sales['gross_profit'].sum():,.2f} EGP"
    )

    print(
        f"\nOutput Directory: {output_dir}"
    )

    print("\nBRONZE TO SILVER TRANSFORMATION COMPLETED!")


# ==================================================
# 11. MAIN FUNCTION
# ==================================================

def main():

    print("=" * 55)
    print("       BRONZE TO SILVER SALES TRANSFORMATION")
    print("=" * 55)

    # Find latest Bronze batch.
    batch_dir = find_latest_batch()

    source_batch_id = batch_dir.name

    print(
        f"\nSource Batch: {source_batch_id}"
    )

    # Load data.
    sales = load_sales(batch_dir)

    products, customers, branches = load_reference_data(
        batch_dir
    )

    original_count = len(sales)

    # Standardize source data.
    standardized_sales = standardize_sales(sales)

    # Validate and separate rejected records.
    valid_sales, quarantined_sales = validate_sales(
        standardized_sales,
        products,
        customers,
        branches,
    )

    print(
        f"\nValid Records: {len(valid_sales):,}"
    )

    print(
        f"Quarantined Records: "
        f"{len(quarantined_sales):,}"
    )

    # Apply business transformations.
    silver_sales = apply_business_transformations(
        valid_sales
    )

    # Save outputs.
    output_dir, manifest = save_outputs(
        silver_sales,
        quarantined_sales,
        batch_dir,
        source_batch_id,
    )

    # Validate final Silver data.
    validate_silver(
        silver_sales,
        quarantined_sales,
        original_count,
    )

    # Print summary.
    print_summary(
        silver_sales,
        quarantined_sales,
        manifest,
        output_dir,
    )


# ==================================================
# 12. SCRIPT ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()
