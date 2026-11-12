
import random
import pandas as pd
from datetime import date
from faker import Faker


from config import (
    RANDOM_SEED,
    NUM_CUSTOMERS,
    NUM_SUPPLIERS,
    RAW_DATA_DIR,
)

# Reproducible synthetic data
random.seed(RANDOM_SEED)

fake = Faker("en_US")
fake.seed_instance(RANDOM_SEED)

EGYPTIAN_CITIES = [
    "Cairo",
    "Giza",
    "Alexandria",
    "Tanta",
    "Mansoura",
    "Damietta",
    "Ismailia",
    "Suez",
]


def generate_customers():
    """Generate synthetic customer records."""

    customers = []

    for i in range(NUM_CUSTOMERS):
        customer = {
            "customer_id": f"C{i + 1:04d}",
            "customer_name": fake.name(),
            "customer_type": random.choice(
                ["Individual", "Business"]
            ),
            "city": random.choice(EGYPTIAN_CITIES),
            "registration_date": fake.date_between(
                start_date=date(2020, 1, 1),
                end_date=date(2025, 12, 31),
            ),
        }

        customers.append(customer)

    return pd.DataFrame(customers)


def generate_suppliers():
    """Generate synthetic supplier records."""

    suppliers = []

    for i in range(NUM_SUPPLIERS):
        supplier = {
            "supplier_id": f"S{i + 1:03d}",
            "supplier_name": fake.company(),
            "city": random.choice(EGYPTIAN_CITIES),
            "contact_email": fake.unique.company_email(),
            "rating": round(random.uniform(2.5, 5.0), 2),
            "is_active": random.random() < 0.9,
        }

        suppliers.append(supplier)

    return pd.DataFrame(suppliers)


def generate_product_suppliers(products_df, suppliers_df):
    """
    Generate Many-to-Many relationships between products
    and suppliers.

    Every product gets at least one supplier.
    Total target: 150 relationships.
    """

    product_ids = products_df["product_id"].tolist()
    supplier_ids = suppliers_df["supplier_id"].tolist()

    # Step 1: Assign one supplier to every product
    relationships = []

    for product_id in product_ids:
        supplier_id = random.choice(supplier_ids)

        relationships.append((product_id, supplier_id))

    existing_pairs = set(relationships)

    # Step 2: Generate 50 additional unique relationships
    all_possible_pairs = [
        (product_id, supplier_id)
        for product_id in product_ids
        for supplier_id in supplier_ids
        if (product_id, supplier_id) not in existing_pairs
    ]

    additional_pairs = random.sample(
        all_possible_pairs,
        50,
    )

    relationships.extend(additional_pairs)

    # Step 3: Build relationship records
    product_lookup = products_df.set_index("product_id")

    records = []

    # Select exactly one preferred supplier per product
    preferred_suppliers = {}

    for product_id in product_ids:
        product_suppliers = [
            supplier_id
            for p_id, supplier_id in relationships
            if p_id == product_id
        ]

        preferred_suppliers[product_id] = random.choice(
            product_suppliers
        )

    for product_id, supplier_id in relationships:

        product = product_lookup.loc[product_id]

        standard_cost = product["standard_cost"]

        supplier_price = round(
            standard_cost * random.uniform(0.90, 1.10),
            2,
        )

        record = {
            "product_id": product_id,
            "supplier_id": supplier_id,
            "supplier_price": supplier_price,
            "lead_time_days": random.randint(2, 14),
            "minimum_order_qty": random.randint(1, 20),
            "is_preferred_supplier": (
                supplier_id
                == preferred_suppliers[product_id]
            ),
        }

        records.append(record)

    return pd.DataFrame(records)


def save_dataframe(df, filename):
    output_path = RAW_DATA_DIR / filename

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved: {output_path}")
    print(f"Records: {len(df)}")


def main():
    print("Starting Customers & Suppliers Generation...")

    # Generate customers
    customers_df = generate_customers()

    # Generate suppliers
    suppliers_df = generate_suppliers()

    # Load existing products
    products_path = RAW_DATA_DIR / "products.csv"
    products_df = pd.read_csv(products_path)

    # Generate product-supplier relationships
    product_suppliers_df = generate_product_suppliers(
        products_df,
        suppliers_df,
    )

    # Save datasets
    save_dataframe(customers_df, "customers.csv")
    save_dataframe(suppliers_df, "suppliers.csv")
    save_dataframe(
        product_suppliers_df,
        "product_suppliers.csv",
    )

    print("\nGeneration Summary:")
    print(f"Customers: {len(customers_df)}")
    print(f"Suppliers: {len(suppliers_df)}")
    print(f"Product-Supplier Relationships: {len(product_suppliers_df)}")

    print("\nRelationships per product:")
    print(
        product_suppliers_df
        .groupby("product_id")
        .size()
        .describe()
    )

    print("\nPreferred supplier count:")
    print(
        product_suppliers_df["is_preferred_supplier"]
        .sum()
    )

    print("\nGeneration Completed Successfully!")


if __name__ == "__main__":
    main()
