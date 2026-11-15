
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


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

REFERENCE_COLUMNS = {
    "products": "product_id",
    "customers": "customer_id",
    "branches": "branch_id",
}


def load_reference_data(batch_dir):
    print("\nLoading reference datasets...")

    references = {}

    for dataset, key_column in REFERENCE_COLUMNS.items():
        path = batch_dir / f"{dataset}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing Bronze reference dataset: {path}"
            )

        reference_df = pd.read_csv(path)

        if key_column not in reference_df.columns:
            raise ValueError(
                f"Bronze {dataset} is missing required column: "
                f"{key_column}"
            )

        references[dataset] = reference_df

    return (
        references["products"],
        references["customers"],
        references["branches"],
    )


def load_sales(batch_dir):
    print("\nLoading Bronze Sales...")

    source_path = batch_dir / "sales.csv"

    if not source_path.exists():
        raise FileNotFoundError(
            f"Bronze sales file not found: {source_path}"
        )

    sales = pd.read_csv(source_path)

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


def standardize_sales(sales):
    print("\nStandardizing data...")

    sales = sales.copy()

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

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

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


def validate_sales(
    sales,
    products,
    customers,
    branches,
):
    print("\nRunning mandatory data quality checks...")

    sales = sales.copy()

    reasons = pd.Series(
        "",
        index=sales.index,
        dtype="string",
    )

    def add_reason(mask, reason):
        nonlocal reasons

        mask = mask.fillna(True)

        reasons.loc[mask] = reasons.loc[mask].apply(
            lambda current: (
                f"{current}; {reason}"
                if current
                else reason
            )
        )

    # Required fields
    for column in REQUIRED_COLUMNS:
        add_reason(
            sales[column].isna(),
            f"MISSING_{column.upper()}",
        )

    # Primary key
    duplicate_ids = sales[
        "sales_line_id"
    ].duplicated(keep=False)

    add_reason(
        duplicate_ids,
        "DUPLICATE_SALES_LINE_ID",
    )

    # Numeric business rules
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

    # Discount cannot exceed gross amount
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

    # Date validation
    add_reason(
        sales["sale_date"].notna()
        & (
            (sales["sale_date"] < pd.Timestamp("2025-01-01"))
            | (sales["sale_date"] > pd.Timestamp("2025-12-31"))
        ),
        "DATE_OUTSIDE_EXPECTED_PERIOD",
    )

    # Sales channel validation
    add_reason(
        sales["sales_channel"].notna()
        & ~sales["sales_channel"].isin(VALID_CHANNELS),
        "INVALID_SALES_CHANNEL",
    )

    # Foreign key validation
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

    # Separate valid and rejected records
    sales["quarantine_reason"] = reasons

    quarantine_mask = reasons.ne("")

    valid_sales = sales.loc[
        ~quarantine_mask
    ].copy()

    quarantined_sales = sales.loc[
        quarantine_mask
    ].copy()

    return valid_sales, quarantined_sales


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

    assert silver_sales["gross_profit"].notna().all(), (
        "Invalid gross profit calculations"
    )

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


def save_outputs(
    silver_sales,
    quarantined_sales,
    source_batch_id,
):
    silver_batch_dir = SILVER_DIR / source_batch_id

    silver_batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    silver_path = silver_batch_dir / "sales.csv"
    quarantine_path = (
        silver_batch_dir / "sales_quarantine.csv"
    )

    silver_sales.to_csv(
        silver_path,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    quarantined_sales.to_csv(
        quarantine_path,
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    loss_count = int(
        silver_sales["is_loss_making"].sum()
    )

    manifest = {
        "dataset": "sales",
        "batch_id": source_batch_id,
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

    print(f"\nOutput Directory: {output_dir}")

    print("\nBRONZE TO SILVER TRANSFORMATION COMPLETED!")


def main(batch_id: str) -> dict:
    if not batch_id or Path(batch_id).name != batch_id:
        raise ValueError(f"Invalid batch_id: {batch_id}")

    print("=" * 55)
    print("       BRONZE TO SILVER SALES TRANSFORMATION")
    print("=" * 55)

    batch_dir = BRONZE_DIR / batch_id

    if not batch_dir.is_dir():
        raise FileNotFoundError(
            f"Bronze batch directory not found: {batch_dir}"
        )

    ingestion_manifest_path = (
        batch_dir / "ingestion_manifest.json"
    )

    if not ingestion_manifest_path.exists():
        raise FileNotFoundError(
            f"Missing ingestion manifest: {ingestion_manifest_path}"
        )

    with open(
        ingestion_manifest_path,
        "r",
        encoding="utf-8",
    ) as file:
        json.load(file)

    print(f"\nSource Batch: {batch_id}")

    # Load source and reference data.
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

    print(f"\nValid Records: {len(valid_sales):,}")

    print(
        f"Quarantined Records: "
        f"{len(quarantined_sales):,}"
    )

    # Apply business transformations.
    silver_sales = apply_business_transformations(
        valid_sales
    )

    # Validate before saving outputs.
    validate_silver(
        silver_sales,
        quarantined_sales,
        original_count,
    )

    # Save outputs only after validation passes.
    output_dir, manifest = save_outputs(
        silver_sales,
        quarantined_sales,
        batch_id,
    )

    # Print summary.
    print_summary(
        silver_sales,
        quarantined_sales,
        manifest,
        output_dir,
    )

    return {
        "batch_id": batch_id,
        "dataset": "sales",
        "input_records": int(manifest["input_records"]),
        "silver_records": int(manifest["silver_records"]),
        "quarantined_records": int(
            manifest["quarantined_records"]
        ),
        "loss_making_records": int(
            manifest["loss_making_records"]
        ),
        "gross_revenue": float(
            silver_sales["gross_amount"].sum()
        ),
        "net_revenue": float(
            silver_sales["net_revenue"].sum()
        ),
        "total_cost": float(
            silver_sales["total_cost"].sum()
        ),
        "gross_profit": float(
            silver_sales["gross_profit"].sum()
        ),
        "status": "SUCCESS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform sales from Bronze to Silver."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Bronze batch ID to process.",
    )

    args = parser.parse_args()
    main(args.batch_id)
