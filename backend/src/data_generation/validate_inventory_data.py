
import pandas as pd

from config import RAW_DATA_DIR


def load_data():

    inventory = pd.read_csv(
        RAW_DATA_DIR / "inventory.csv",
        parse_dates=["snapshot_date"],
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    warehouses = pd.read_csv(
        RAW_DATA_DIR / "warehouses.csv"
    )

    return inventory, products, warehouses


def validate_basic_rules(inventory):

    print("\nValidating Basic Rules...")

    assert len(inventory) == 9000, (
        "Incorrect inventory record count"
    )

    assert inventory["inventory_snapshot_id"].is_unique, (
        "Duplicate inventory snapshot IDs"
    )

    required_columns = [
        "product_id",
        "warehouse_id",
        "snapshot_date",
        "quantity_on_hand",
        "quantity_reserved",
    ]

    assert inventory[required_columns].notna().all().all(), (
        "Null values found in required columns"
    )

    assert (inventory["quantity_on_hand"] >= 0).all(), (
        "Negative on-hand quantities found"
    )

    assert (inventory["quantity_reserved"] >= 0).all(), (
        "Negative reserved quantities found"
    )

    print("Basic Rules Passed!")


def validate_composite_key(inventory):

    print("\nValidating Composite Key...")

    duplicate_rows = inventory.duplicated(
        subset=[
            "product_id",
            "warehouse_id",
            "snapshot_date",
        ]
    )

    assert not duplicate_rows.any(), (
        "Duplicate Product-Warehouse-Date combinations found"
    )

    print("Composite Key Validation Passed!")


def validate_foreign_keys(
    inventory,
    products,
    warehouses,
):

    print("\nValidating Foreign Keys...")

    valid_products = set(products["product_id"])

    valid_warehouses = set(warehouses["warehouse_id"])

    assert set(inventory["product_id"]).issubset(
        valid_products
    ), "Unknown product IDs found"

    assert set(inventory["warehouse_id"]).issubset(
        valid_warehouses
    ), "Unknown warehouse IDs found"

    print("Foreign Key Validation Passed!")


def validate_inventory_constraints(inventory):

    print("\nValidating Inventory Constraints...")

    invalid_reservations = (
        inventory["quantity_reserved"]
        > inventory["quantity_on_hand"]
    )

    assert not invalid_reservations.any(), (
        "Reserved quantity exceeds on-hand quantity"
    )

    inventory["available_stock"] = (
        inventory["quantity_on_hand"]
        - inventory["quantity_reserved"]
    )

    assert (inventory["available_stock"] >= 0).all(), (
        "Negative available stock found"
    )

    print("Inventory Constraints Passed!")


def validate_snapshot_coverage(inventory):

    print("\nValidating Snapshot Coverage...")

    assert inventory["product_id"].nunique() == 100, (
        "Incorrect number of products"
    )

    assert inventory["warehouse_id"].nunique() == 3, (
        "Incorrect number of warehouses"
    )

    assert inventory["snapshot_date"].nunique() == 30, (
        "Incorrect number of snapshot dates"
    )

    expected_combinations = 100 * 3 * 30

    assert len(inventory) == expected_combinations, (
        "Missing product-warehouse-date combinations"
    )

    print("Snapshot Coverage Passed!")


def display_inventory_summary(inventory):

    print("\n========== INVENTORY QUALITY SUMMARY ==========")

    inventory["available_stock"] = (
        inventory["quantity_on_hand"]
        - inventory["quantity_reserved"]
    )

    print(f"Total Records: {len(inventory)}")

    print(
        f"Total On-Hand Quantity: "
        f"{inventory['quantity_on_hand'].sum():,}"
    )

    print(
        f"Total Reserved Quantity: "
        f"{inventory['quantity_reserved'].sum():,}"
    )

    print(
        f"Total Available Quantity: "
        f"{inventory['available_stock'].sum():,}"
    )

    print(
        f"Stockout Records: "
        f"{(inventory['quantity_on_hand'] == 0).sum():,}"
    )

    print(
        f"Average On-Hand Quantity: "
        f"{inventory['quantity_on_hand'].mean():,.2f}"
    )

    print("\nInventory by Warehouse:")

    print(
        inventory.groupby("warehouse_id")[
            "quantity_on_hand"
        ].sum()
    )

    print("\n================================================")


def main():

    print("Starting Inventory Data Validation...")

    inventory, products, warehouses = load_data()

    validate_basic_rules(inventory)

    validate_composite_key(inventory)

    validate_foreign_keys(
        inventory,
        products,
        warehouses,
    )

    validate_inventory_constraints(inventory)

    validate_snapshot_coverage(inventory)

    display_inventory_summary(inventory)

    print("\nALL INVENTORY VALIDATIONS PASSED!")


if __name__ == "__main__":
    main()
