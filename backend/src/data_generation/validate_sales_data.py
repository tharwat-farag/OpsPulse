
import pandas as pd

from config import (
    NUM_SALES_LINES,
    START_DATE,
    END_DATE,
    RAW_DATA_DIR,
)


def load_data():
    sales = pd.read_csv(
        RAW_DATA_DIR / "sales.csv",
        parse_dates=["sale_date"],
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    customers = pd.read_csv(
        RAW_DATA_DIR / "customers.csv"
    )

    branches = pd.read_csv(
        RAW_DATA_DIR / "branches.csv"
    )

    return sales, products, customers, branches


def validate_basic_rules(sales):
    print("\nValidating Basic Sales Rules...")

    assert len(sales) == NUM_SALES_LINES, (
        "Incorrect number of sales records"
    )

    assert sales["sales_line_id"].is_unique, (
        "Duplicate sales line IDs"
    )

    assert sales["sales_line_id"].notna().all(), (
        "Null sales line IDs"
    )

    assert sales["invoice_id"].notna().all(), (
        "Null invoice IDs"
    )

    required_columns = [
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

    assert sales[required_columns].notna().all().all(), (
        "Null values found in required columns"
    )

    assert (sales["quantity"] > 0).all(), (
        "Invalid sales quantities"
    )

    assert (sales["unit_price"] > 0).all(), (
        "Invalid selling prices"
    )

    assert (sales["unit_cost"] > 0).all(), (
        "Invalid unit costs"
    )

    assert (sales["discount_amount"] >= 0).all(), (
        "Negative discounts found"
    )

    gross_amount = sales["quantity"] * sales["unit_price"]

    assert (
        sales["discount_amount"] <= gross_amount
    ).all(), "Discount exceeds gross sales amount"

    valid_channels = {
        "In-Store",
        "Online",
        "Phone",
    }

    assert set(sales["sales_channel"]).issubset(
        valid_channels
    ), "Invalid sales channels"

    print("Basic Sales Rules Passed!")


def validate_foreign_keys(
    sales,
    products,
    customers,
    branches,
):
    print("\nValidating Foreign Keys...")

    valid_product_ids = set(products["product_id"])
    valid_customer_ids = set(customers["customer_id"])
    valid_branch_ids = set(branches["branch_id"])

    assert set(sales["product_id"]).issubset(
        valid_product_ids
    ), "Unknown product IDs found"

    assert set(sales["customer_id"]).issubset(
        valid_customer_ids
    ), "Unknown customer IDs found"

    assert set(sales["branch_id"]).issubset(
        valid_branch_ids
    ), "Unknown branch IDs found"

    print("Foreign Key Validation Passed!")


def validate_dates(sales):
    print("\nValidating Sales Dates...")

    assert sales["sale_date"].between(
        pd.Timestamp(START_DATE),
        pd.Timestamp(END_DATE),
    ).all(), "Sales dates outside the expected period"

    print("Sales Date Validation Passed!")


def validate_invoices(sales):
    print("\nValidating Invoice Rules...")

    invoice_groups = sales.groupby("invoice_id")

    # Each invoice must contain between 1 and 4 lines.
    lines_per_invoice = invoice_groups.size()

    assert lines_per_invoice.between(1, 4).all(), (
        "Invoice contains an invalid number of lines"
    )

    # All lines in one invoice must share the same customer.
    assert (
        invoice_groups["customer_id"].nunique() == 1
    ).all(), "Different customers found in the same invoice"

    # All lines in one invoice must share the same branch.
    assert (
        invoice_groups["branch_id"].nunique() == 1
    ).all(), "Different branches found in the same invoice"

    # All lines in one invoice must share the same date.
    assert (
        invoice_groups["sale_date"].nunique() == 1
    ).all(), "Different dates found in the same invoice"

    # All lines in one invoice must share the same channel.
    assert (
        invoice_groups["sales_channel"].nunique() == 1
    ).all(), "Different channels found in the same invoice"

    # A product must not appear twice in the same invoice.
    assert not sales.duplicated(
        subset=["invoice_id", "product_id"]
    ).any(), "Duplicate products found within an invoice"

    print("Invoice Validation Passed!")


def display_sales_metrics(sales):
    print("\n========== SALES QUALITY SUMMARY ==========")

    print(f"Total Sales Lines: {len(sales)}")

    print(f"Unique Invoices: {sales['invoice_id'].nunique()}")

    print(
        f"Unique Products: {sales['product_id'].nunique()}"
    )

    print(
        f"Unique Customers: {sales['customer_id'].nunique()}"
    )

    print(
        f"Unique Branches: {sales['branch_id'].nunique()}"
    )

    # Business calculations
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

    print(
        f"\nTotal Gross Amount: "
        f"{sales['gross_amount'].sum():,.2f}"
    )

    print(
        f"Total Discounts: "
        f"{sales['discount_amount'].sum():,.2f}"
    )

    print(
        f"Total Net Revenue: "
        f"{sales['net_revenue'].sum():,.2f}"
    )

    print(
        f"Total Cost: "
        f"{sales['total_cost'].sum():,.2f}"
    )

    print(
        f"Total Gross Profit: "
        f"{sales['gross_profit'].sum():,.2f}"
    )

    print("\n===========================================")


def main():
    print("Starting Sales Data Validation...")

    sales, products, customers, branches = load_data()

    validate_basic_rules(sales)

    validate_foreign_keys(
        sales,
        products,
        customers,
        branches,
    )

    validate_dates(sales)

    validate_invoices(sales)

    display_sales_metrics(sales)

    print("\nALL SALES DATA VALIDATIONS PASSED!")


if __name__ == "__main__":
    main()
