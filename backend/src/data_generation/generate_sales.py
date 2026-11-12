
import random
import pandas as pd

from datetime import timedelta

from config import (
    RANDOM_SEED,
    NUM_SALES_LINES,
    START_DATE,
    END_DATE,
    RAW_DATA_DIR,
)

# Reproducible data generation
random.seed(RANDOM_SEED)


def load_reference_data():
    """
    Load reference datasets required for sales generation.
    """

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    customers = pd.read_csv(
        RAW_DATA_DIR / "customers.csv"
    )

    branches = pd.read_csv(
        RAW_DATA_DIR / "branches.csv"
    )

    return products, customers, branches


def generate_sales(products, customers, branches):
    """
    Generate synthetic sales at invoice-line level.

    Each row represents one product inside an invoice.
    """

    sales = []

    # Convert products DataFrame into a dictionary
    # for faster product lookup.
    product_lookup = (
        products.set_index("product_id")
        .to_dict(orient="index")
    )

    product_ids = list(product_lookup.keys())

    customer_ids = customers["customer_id"].tolist()

    branch_ids = branches["branch_id"].tolist()

    sales_line_number = 1
    invoice_number = 1

    total_days = (END_DATE - START_DATE).days

    while sales_line_number <= NUM_SALES_LINES:

        # Determine how many products are in this invoice.
        remaining_lines = (
            NUM_SALES_LINES - sales_line_number + 1
        )

        lines_in_invoice = random.randint(
            1,
            min(4, remaining_lines),
        )

        # Select different products for the same invoice.
        selected_products = random.sample(
            product_ids,
            lines_in_invoice,
        )

        # Shared invoice information.
        invoice_id = f"INV{invoice_number:06d}"

        sale_date = START_DATE + timedelta(
            days=random.randint(0, total_days)
        )

        customer_id = random.choice(customer_ids)

        branch_id = random.choice(branch_ids)

        sales_channel = random.choice([
            "In-Store",
            "Online",
            "Phone",
        ])

        # Generate one row for each product.
        for product_id in selected_products:

            product = product_lookup[product_id]

            quantity = random.randint(1, 10)

            # Historical selling price variation.
            unit_price = round(
                product["current_selling_price"]
                * random.uniform(0.95, 1.08),
                2,
            )

            # Historical cost variation.
            unit_cost = round(
                product["standard_cost"]
                * random.uniform(0.98, 1.04),
                2,
            )

            gross_amount = quantity * unit_price

            discount_rate = random.uniform(0, 0.12)

            discount_amount = round(
                gross_amount * discount_rate,
                2,
            )

            sales.append({
                "sales_line_id": (
                    f"SL{sales_line_number:06d}"
                ),
                "invoice_id": invoice_id,
                "sale_date": sale_date,
                "product_id": product_id,
                "customer_id": customer_id,
                "branch_id": branch_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "discount_amount": discount_amount,
                "sales_channel": sales_channel,
            })

            sales_line_number += 1

        invoice_number += 1

    return pd.DataFrame(sales)


def save_sales_data(sales_df):
    """
    Save generated sales data to CSV.
    """

    output_path = RAW_DATA_DIR / "sales.csv"

    sales_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nSaved: {output_path}")


def display_summary(sales_df):
    """
    Display generation statistics.
    """

    print("\n========== SALES GENERATION SUMMARY ==========")

    print(f"Total Sales Lines: {len(sales_df)}")

    print(
        f"Unique Invoices: "
        f"{sales_df['invoice_id'].nunique()}"
    )

    print(
        f"Unique Products Sold: "
        f"{sales_df['product_id'].nunique()}"
    )

    print(
        f"Unique Customers: "
        f"{sales_df['customer_id'].nunique()}"
    )

    print(
        f"Unique Branches: "
        f"{sales_df['branch_id'].nunique()}"
    )

    print("\nSales Preview:")
    print(sales_df.head())

    print("\nSales by Channel:")
    print(sales_df["sales_channel"].value_counts())

    print("\nSales by Branch:")
    print(sales_df["branch_id"].value_counts())

    print("\nSales Date Range:")

    print(f"Minimum Date: {sales_df['sale_date'].min()}")

    print(f"Maximum Date: {sales_df['sale_date'].max()}")

    print("\n===============================================")


def main():

    print("Starting Sales Data Generation...")

    # Load reference datasets.
    products, customers, branches = load_reference_data()

    # Generate sales.
    sales_df = generate_sales(
        products,
        customers,
        branches,
    )

    # Save generated data.
    save_sales_data(sales_df)

    # Display summary.
    display_summary(sales_df)

    print("\nSales Data Generation Completed Successfully!")


if __name__ == "__main__":
    main()
