
import pandas as pd

from pathlib import Path


# ==================================================
# 1. PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"


# ==================================================
# 2. FIND LATEST BRONZE BATCH
# ==================================================

def find_latest_batch():

    batch_dirs = sorted(
        [
            path
            for path in BRONZE_DIR.glob("batch_*")
            if (path / "ingestion_manifest.json").exists()
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not batch_dirs:

        raise FileNotFoundError(
            "No Bronze ingestion batch found."
        )

    return batch_dirs[0]


# ==================================================
# 3. LOAD DATASETS
# ==================================================

def load_data(batch_dir):

    print("\nLoading Bronze datasets...")

    sales = pd.read_csv(
        batch_dir / "sales.csv"
    )

    products = pd.read_csv(
        batch_dir / "products.csv"
    )

    customers = pd.read_csv(
        batch_dir / "customers.csv"
    )

    branches = pd.read_csv(
        batch_dir / "branches.csv"
    )

    return sales, products, customers, branches


# ==================================================
# 4. BASIC DATA PROFILE
# ==================================================

def basic_profile(df):

    print("\n========== BASIC PROFILE ==========")

    print(f"Rows: {df.shape[0]:,}")

    print(f"Columns: {df.shape[1]}")

    print("\nColumn Names:")

    print(df.columns.tolist())

    print("\nData Types:")

    print(df.dtypes)

    print("\nMissing Values:")

    print(df.isnull().sum())

    print("\nDuplicate Rows:")

    print(df.duplicated().sum())


# ==================================================
# 5. KEY PROFILE
# ==================================================

def key_profile(sales):

    print("\n========== KEY PROFILE ==========")

    print(
        "Duplicate Sales Line IDs:",
        sales["sales_line_id"].duplicated().sum()
    )

    print(
        "Unique Invoices:",
        sales["invoice_id"].nunique()
    )

    print(
        "Unique Products:",
        sales["product_id"].nunique()
    )

    print(
        "Unique Customers:",
        sales["customer_id"].nunique()
    )

    print(
        "Unique Branches:",
        sales["branch_id"].nunique()
    )


# ==================================================
# 6. NUMERIC PROFILE
# ==================================================

def numeric_profile(sales):

    print("\n========== NUMERIC PROFILE ==========")

    numeric_columns = [
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
    ]

    print(
        sales[numeric_columns].describe()
    )

    print(
        "\nInvalid Quantity:",
        (sales["quantity"] <= 0).sum()
    )

    print(
        "Invalid Unit Price:",
        (sales["unit_price"] <= 0).sum()
    )

    print(
        "Invalid Unit Cost:",
        (sales["unit_cost"] <= 0).sum()
    )

    print(
        "Negative Discounts:",
        (sales["discount_amount"] < 0).sum()
    )

    gross_amount = (
        sales["quantity"] * sales["unit_price"]
    )

    print(
        "Discounts Greater Than Gross Amount:",
        (sales["discount_amount"] > gross_amount).sum()
    )


# ==================================================
# 7. DATE PROFILE
# ==================================================

def date_profile(sales):

    print("\n========== DATE PROFILE ==========")

    dates = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

    print(
        "Invalid Dates:",
        dates.isna().sum()
    )

    print(
        "Minimum Date:",
        dates.min()
    )

    print(
        "Maximum Date:",
        dates.max()
    )

    outside_2025 = (
        (dates < pd.Timestamp("2025-01-01"))
        | (dates > pd.Timestamp("2025-12-31"))
    )

    print(
        "Dates Outside 2025:",
        outside_2025.sum()
    )


# ==================================================
# 8. FOREIGN KEY PROFILE
# ==================================================

def foreign_key_profile(
    sales,
    products,
    customers,
    branches,
):

    print("\n========== FOREIGN KEY PROFILE ==========")

    checks = {
        "product_id": set(products["product_id"]),
        "customer_id": set(customers["customer_id"]),
        "branch_id": set(branches["branch_id"]),
    }

    for column, valid_ids in checks.items():

        invalid_count = (
            ~sales[column].isin(valid_ids)
        ).sum()

        print(
            f"Invalid {column}: {invalid_count}"
        )


# ==================================================
# 9. ADVANCED BUSINESS PROFILE
# ==================================================

def advanced_business_profile(sales):

    print(
        "\n========== ADVANCED BUSINESS PROFILE =========="
    )

    sales = sales.copy()

    # Calculate financial values
    sales["gross_amount"] = (
        sales["quantity"] * sales["unit_price"]
    )

    sales["net_revenue"] = (
        sales["gross_amount"] - sales["discount_amount"]
    )

    sales["total_cost"] = (
        sales["quantity"] * sales["unit_cost"]
    )

    sales["gross_profit"] = (
        sales["net_revenue"] - sales["total_cost"]
    )

    # Unit cost greater than selling price
    cost_greater_than_price = (
        sales["unit_cost"] > sales["unit_price"]
    )

    print(
        "\nUnit Cost Greater Than Unit Price:",
        cost_greater_than_price.sum()
    )

    # Negative gross profit
    loss_records = (
        sales["gross_profit"] < 0
    )

    print(
        "Sales Lines With Negative Gross Profit:",
        loss_records.sum()
    )

    # Discount rate
    sales["discount_rate"] = (
        sales["discount_amount"]
        / sales["gross_amount"]
    )

    print("\nDiscount Rate Statistics:")

    print(
        sales["discount_rate"].describe()
    )

    print(
        "Discount Rate Above 50%:",
        (sales["discount_rate"] > 0.50).sum()
    )

    # Sales channel validation
    print("\nSales Channel Values:")

    print(
        sales["sales_channel"].value_counts()
    )

    valid_channels = {
        "In-Store",
        "Phone",
        "Online",
    }

    invalid_channels = (
        ~sales["sales_channel"].isin(valid_channels)
    )

    print(
        "Invalid Sales Channels:",
        invalid_channels.sum()
    )

    # Invoice consistency
    consistency_columns = [
        "sale_date",
        "customer_id",
        "branch_id",
        "sales_channel",
    ]

    invoice_consistency = (
        sales.groupby("invoice_id")[consistency_columns]
        .nunique()
    )

    inconsistent_invoices = (
        invoice_consistency > 1
    ).any(axis=1)

    print(
        "\nInconsistent Invoices:",
        inconsistent_invoices.sum()
    )

    # Duplicate products within invoice
    duplicate_invoice_products = sales.duplicated(
        subset=["invoice_id", "product_id"],
        keep=False,
    )

    print(
        "Duplicate Products Within Same Invoice:",
        duplicate_invoice_products.sum()
    )

    # Financial summary
    print(
        "\n========== FINANCIAL SUMMARY =========="
    )

    print(
        f"Gross Revenue: "
        f"{sales['gross_amount'].sum():,.2f} EGP"
    )

    print(
        f"Discounts: "
        f"{sales['discount_amount'].sum():,.2f} EGP"
    )

    print(
        f"Net Revenue: "
        f"{sales['net_revenue'].sum():,.2f} EGP"
    )

    print(
        f"Total Cost: "
        f"{sales['total_cost'].sum():,.2f} EGP"
    )

    print(
        f"Gross Profit: "
        f"{sales['gross_profit'].sum():,.2f} EGP"
    )

    if sales["net_revenue"].sum() != 0:

        gross_profit_margin = (
            sales["gross_profit"].sum()
            / sales["net_revenue"].sum()
        ) * 100

        print(
            f"Gross Profit Margin: "
            f"{gross_profit_margin:.2f}%"
        )


# ==================================================
# 10. INVESTIGATE LOSS RECORDS
# ==================================================

def investigate_loss_records(sales, products):

    print(
        "\n========== LOSS RECORD INVESTIGATION =========="
    )

    # Work on a copy. Never modify Bronze data.
    investigation = sales.copy()

    # Calculate financial values
    investigation["gross_amount"] = (
        investigation["quantity"]
        * investigation["unit_price"]
    )

    investigation["net_revenue"] = (
        investigation["gross_amount"]
        - investigation["discount_amount"]
    )

    investigation["total_cost"] = (
        investigation["quantity"]
        * investigation["unit_cost"]
    )

    investigation["gross_profit"] = (
        investigation["net_revenue"]
        - investigation["total_cost"]
    )

    investigation["discount_rate"] = (
        investigation["discount_amount"]
        / investigation["gross_amount"]
    )

    # Select loss-making records
    loss_records = investigation[
        investigation["gross_profit"] < 0
    ].copy()

    print(
        f"\nTotal Loss Records: {len(loss_records):,}"
    )

    print(
        f"Total Loss Amount: "
        f"{loss_records['gross_profit'].sum():,.2f} EGP"
    )

    # Add product information
    product_info = products[
        ["product_id", "product_name", "category"]
    ]

    loss_records = loss_records.merge(
        product_info,
        on="product_id",
        how="left",
        validate="many_to_one",
    )

    # Display sample records
    print("\nSample Loss Records:")

    columns_to_display = [
        "sales_line_id",
        "invoice_id",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
        "discount_rate",
        "net_revenue",
        "total_cost",
        "gross_profit",
        "sales_channel",
    ]

    if not loss_records.empty:

        print(
            loss_records[columns_to_display]
            .head(20)
            .to_string(index=False)
        )

    else:

        print("No loss-making records found.")

    # Loss analysis by product category
    print("\nLoss Records By Category:")

    if not loss_records.empty:

        category_summary = (
            loss_records.groupby("category")
            .agg(
                loss_records=("sales_line_id", "count"),
                total_loss=("gross_profit", "sum"),
                average_loss=("gross_profit", "mean"),
            )
            .sort_values("total_loss")
        )

        print(category_summary)

    # Loss analysis by sales channel
    print("\nLoss Records By Sales Channel:")

    if not loss_records.empty:

        channel_summary = (
            loss_records.groupby("sales_channel")
            .agg(
                loss_records=("sales_line_id", "count"),
                total_loss=("gross_profit", "sum"),
            )
            .sort_values("total_loss")
        )

        print(channel_summary)

    # Discount rate analysis
    print("\nDiscount Rate In Loss Records:")

    if not loss_records.empty:

        print(
            loss_records["discount_rate"].describe()
        )


# ==================================================
# 11. MAIN FUNCTION
# ==================================================

def main():

    print("=" * 55)

    print(
        "             SALES DATA PROFILING"
    )

    print("=" * 55)

    # Find latest Bronze batch
    batch_dir = find_latest_batch()

    print(
        f"\nUsing Batch: {batch_dir.name}"
    )

    # Load datasets
    sales, products, customers, branches = load_data(
        batch_dir
    )

    # Run profiling
    basic_profile(sales)

    key_profile(sales)

    numeric_profile(sales)

    date_profile(sales)

    foreign_key_profile(
        sales,
        products,
        customers,
        branches,
    )

    advanced_business_profile(sales)

    investigate_loss_records(
        sales,
        products,
    )

    print("\n" + "=" * 55)

    print(
        "          PROFILING COMPLETED"
    )

    print("=" * 55)


# ==================================================
# 12. SCRIPT ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()
