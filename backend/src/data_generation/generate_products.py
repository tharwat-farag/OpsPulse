
import random
import pandas as pd

from config import (
    RANDOM_SEED,
    NUM_PRODUCTS,
    RAW_DATA_DIR,
)

# -----------------------------------
# 1. Initialize Random Generator
# -----------------------------------

random.seed(RANDOM_SEED)


# -----------------------------------
# 2. Product Categories Configuration
# -----------------------------------

PRODUCT_CATEGORIES = {
    "Electronics": {
        "cost_range": (2000, 15000),
        "margin_range": (0.10, 0.25),
        "brands": ["Samsung", "Dell", "HP", "Lenovo"],
        "product_types": ["Laptop", "Monitor", "Tablet", "Printer"],
    },

    "Accessories": {
        "cost_range": (100, 1000),
        "margin_range": (0.20, 0.45),
        "brands": ["Logitech", "Anker", "Baseus", "JBL"],
        "product_types": ["Mouse", "Keyboard", "Headset", "Cable"],
    },

    "Home Appliances": {
        "cost_range": (1000, 10000),
        "margin_range": (0.12, 0.30),
        "brands": ["Toshiba", "Samsung", "Fresh", "LG"],
        "product_types": ["Fan", "Blender", "Microwave", "Vacuum"],
    },

    "Office Supplies": {
        "cost_range": (20, 500),
        "margin_range": (0.15, 0.35),
        "brands": ["Deli", "Pilot", "Staedtler", "Avery"],
        "product_types": ["Notebook", "Pen", "Folder", "Stapler"],
    },

    "Furniture": {
        "cost_range": (500, 5000),
        "margin_range": (0.15, 0.35),
        "brands": ["Modern Office", "WoodCraft", "Comfort"],
        "product_types": ["Desk", "Chair", "Cabinet", "Shelf"],
    },
}


# -----------------------------------
# 3. Generate Products
# -----------------------------------

def generate_products():

    products = []

    categories = list(PRODUCT_CATEGORIES.keys())

    for i in range(NUM_PRODUCTS):

        # Select a category
        category = random.choice(categories)

        category_config = PRODUCT_CATEGORIES[category]

        # Generate product details
        brand = random.choice(category_config["brands"])
        product_type = random.choice(category_config["product_types"])

        # Generate cost
        min_cost, max_cost = category_config["cost_range"]

        standard_cost = round(
            random.uniform(min_cost, max_cost), 2
        )

        # Generate selling price
        min_margin, max_margin = category_config["margin_range"]

        margin = random.uniform(min_margin, max_margin)

        selling_price = round(
            standard_cost * (1 + margin), 2
        )

        # Generate reorder level
        reorder_level = random.randint(10, 100)

        product = {
            "product_id": f"P{i + 1:03d}",
            "product_name": f"{brand} {product_type} {i + 1:03d}",
            "category": category,
            "brand": brand,
            "standard_cost": standard_cost,
            "current_selling_price": selling_price,
            "reorder_level": reorder_level,
            "is_active": random.random() < 0.95,
        }

        products.append(product)

    return pd.DataFrame(products)


# -----------------------------------
# 4. Save Products
# -----------------------------------

def main():

    print("Generating Products...")

    products_df = generate_products()

    output_path = RAW_DATA_DIR / "products.csv"

    products_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved: {output_path}")
    print(f"Records: {len(products_df)}")

    print("\nProduct Preview:")
    print(products_df.head())

    print("\nProducts by Category:")
    print(products_df["category"].value_counts())


if __name__ == "__main__":
    main()
