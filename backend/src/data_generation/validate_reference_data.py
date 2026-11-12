
import pandas as pd

from config import (
    NUM_BRANCHES,
    NUM_WAREHOUSES,
    NUM_PRODUCTS,
    RAW_DATA_DIR,
)


# -----------------------------------
# 1. Generic Dataset Validation
# -----------------------------------

def validate_dataset(df, dataset_name, id_column, expected_count):

    print(f"\nValidating {dataset_name}...")

    # Check record count
    assert len(df) == expected_count, (
        f"Expected {expected_count} records, got {len(df)}"
    )

    # Check unique IDs
    assert df[id_column].is_unique, (
        f"Duplicate values found in {id_column}"
    )

    # Check missing values
    assert not df.isnull().any().any(), (
        f"Missing values detected in {dataset_name}"
    )

    print("Validation passed!")
    print(f"Records: {len(df)}")
    print(f"Unique IDs: {df[id_column].nunique()}")


# -----------------------------------
# 2. Products Validation
# -----------------------------------

def validate_products(df):

    print("\nValidating Products...")

    # Check record count
    assert len(df) == NUM_PRODUCTS, (
        f"Expected {NUM_PRODUCTS} products, got {len(df)}"
    )

    # Check unique product IDs
    assert df["product_id"].is_unique, (
        "Duplicate product IDs found"
    )

    # Check missing values
    assert not df.isnull().any().any(), (
        "Missing values detected in Products"
    )

    # Check product cost
    assert (df["standard_cost"] > 0).all(), (
        "Invalid product cost"
    )

    # Check selling price
    assert (
        df["current_selling_price"] > df["standard_cost"]
    ).all(), (
        "Selling price must exceed standard cost"
    )

    # Check reorder level
    assert (df["reorder_level"] > 0).all(), (
        "Invalid reorder level"
    )

    # Check product categories
    expected_categories = {
        "Electronics",
        "Accessories",
        "Home Appliances",
        "Office Supplies",
        "Furniture",
    }

    actual_categories = set(df["category"].unique())

    assert actual_categories.issubset(expected_categories), (
        "Unexpected product category found"
    )

    print("Products validation passed!")
    print(f"Records: {len(df)}")
    print(f"Categories: {df['category'].nunique()}")


# -----------------------------------
# 3. Main Execution
# -----------------------------------

def main():

    print("=" * 45)
    print("OPSPULSE - REFERENCE DATA VALIDATION")
    print("=" * 45)

    # Load Branches
    branches = pd.read_csv(
        RAW_DATA_DIR / "branches.csv"
    )

    # Load Warehouses
    warehouses = pd.read_csv(
        RAW_DATA_DIR / "warehouses.csv"
    )

    # Load Products
    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    # Validate Branches
    validate_dataset(
        branches,
        "Branches",
        "branch_id",
        NUM_BRANCHES
    )

    # Validate Warehouses
    validate_dataset(
        warehouses,
        "Warehouses",
        "warehouse_id",
        NUM_WAREHOUSES
    )

    # Validate Products
    validate_products(products)

    print("\n" + "=" * 45)
    print("ALL REFERENCE DATA VALIDATIONS PASSED!")
    print("=" * 45)


if __name__ == "__main__":
    main()
