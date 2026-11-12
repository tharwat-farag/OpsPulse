
import random
import pandas as pd

from datetime import timedelta

from config import (
    RANDOM_SEED,
    START_DATE,
    END_DATE,
    RAW_DATA_DIR,
)

random.seed(RANDOM_SEED)

# Business simulation settings
INITIAL_UTILIZATION_MIN = 0.50
INITIAL_UTILIZATION_MAX = 0.60

MAX_CAPACITY_UTILIZATION = 0.85

STOCK_CHANGE_MIN = -8
STOCK_CHANGE_MAX = 8

STOCKOUT_PROBABILITY = 0.03


def load_products():
    """Load product reference data."""
    return pd.read_csv(RAW_DATA_DIR / "products.csv")


def load_warehouses():
    """Load warehouse reference data."""
    return pd.read_csv(RAW_DATA_DIR / "warehouses.csv")


def generate_snapshot_dates():
    """Generate 30 snapshot dates across 2025."""

    total_days = (END_DATE - START_DATE).days
    interval = total_days // 29

    dates = [
        START_DATE + timedelta(days=i * interval)
        for i in range(29)
    ]

    dates.append(END_DATE)

    return dates


def distribute_stock(total_stock, product_ids):
    """
    Distribute a warehouse's total stock across products.

    Uses random weights and the largest-remainder method
    to preserve the exact total quantity.
    """

    weights = {
        product_id: random.uniform(0.5, 1.5)
        for product_id in product_ids
    }

    total_weight = sum(weights.values())

    quotas = {
        product_id: total_stock * weight / total_weight
        for product_id, weight in weights.items()
    }

    allocations = {
        product_id: int(quota)
        for product_id, quota in quotas.items()
    }

    remaining = total_stock - sum(allocations.values())

    sorted_products = sorted(
        product_ids,
        key=lambda product_id: (
            quotas[product_id] - allocations[product_id]
        ),
        reverse=True,
    )

    for product_id in sorted_products[:remaining]:
        allocations[product_id] += 1

    return allocations


def enforce_capacity(stock_levels, product_ids, max_stock):
    """
    Keep total warehouse stock within the configured limit.

    If proposed stock exceeds the limit, redistribute it
    proportionally while preserving integer quantities.
    """

    current_total = sum(
        stock_levels[product_id]
        for product_id in product_ids
    )

    if current_total <= max_stock:
        return stock_levels

    adjusted_stock = distribute_stock(
        max_stock,
        product_ids
    )

    for product_id in product_ids:
        stock_levels[product_id] = adjusted_stock[product_id]

    return stock_levels


def generate_inventory(products, warehouses):

    snapshot_dates = generate_snapshot_dates()

    records = []
    snapshot_number = 1

    product_ids = products["product_id"].tolist()

    # Store stock separately for each warehouse and product.
    stock_levels = {}

    # Define the maximum allowed stock for each warehouse.
    warehouse_stock_limits = {}

    # Generate initial inventory based on warehouse capacity.
    for _, warehouse in warehouses.iterrows():

        warehouse_id = warehouse["warehouse_id"]
        capacity = int(warehouse["capacity_units"])

        target_utilization = random.uniform(
            INITIAL_UTILIZATION_MIN,
            INITIAL_UTILIZATION_MAX
        )

        initial_total_stock = int(
            capacity * target_utilization
        )

        max_stock = int(
            capacity * MAX_CAPACITY_UTILIZATION
        )

        warehouse_stock_limits[warehouse_id] = max_stock

        initial_allocations = distribute_stock(
            initial_total_stock,
            product_ids
        )

        for product_id in product_ids:
            stock_levels[(product_id, warehouse_id)] = (
                initial_allocations[product_id]
            )

    # Generate inventory snapshots over time.
    for snapshot_date in snapshot_dates:

        for _, warehouse in warehouses.iterrows():

            warehouse_id = warehouse["warehouse_id"]

            # Generate stock changes for all products in this warehouse.
            warehouse_stock = {}

            for product_id in product_ids:

                key = (product_id, warehouse_id)

                previous_stock = stock_levels[key]

                stock_change = random.randint(
                    STOCK_CHANGE_MIN,
                    STOCK_CHANGE_MAX
                )

                quantity_on_hand = max(
                    0,
                    previous_stock + stock_change
                )

                # Occasionally simulate a stockout.
                if random.random() < STOCKOUT_PROBABILITY:
                    quantity_on_hand = 0

                warehouse_stock[product_id] = quantity_on_hand

            # Enforce the warehouse's operational capacity limit.
            warehouse_stock = enforce_capacity(
                warehouse_stock,
                product_ids,
                warehouse_stock_limits[warehouse_id]
            )

            # Create one snapshot record per product/warehouse.
            for product_id in product_ids:

                quantity_on_hand = warehouse_stock[product_id]

                quantity_reserved = random.randint(
                    0,
                    min(
                        quantity_on_hand,
                        max(
                            0,
                            int(quantity_on_hand * 0.30)
                        ),
                    ),
                )

                records.append({
                    "inventory_snapshot_id": (
                        f"IS{snapshot_number:06d}"
                    ),
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "snapshot_date": snapshot_date,
                    "quantity_on_hand": quantity_on_hand,
                    "quantity_reserved": quantity_reserved,
                })

                stock_levels[(product_id, warehouse_id)] = (
                    quantity_on_hand
                )

                snapshot_number += 1

    return pd.DataFrame(records)


def main():

    print("Starting Inventory Data Generation...")

    products = load_products()
    warehouses = load_warehouses()

    inventory_df = generate_inventory(
        products,
        warehouses
    )

    output_path = RAW_DATA_DIR / "inventory.csv"

    inventory_df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nSaved: {output_path}")
    print(f"Total Records: {len(inventory_df)}")

    print(
        f"Unique Products: "
        f"{inventory_df['product_id'].nunique()}"
    )

    print(
        f"Unique Warehouses: "
        f"{inventory_df['warehouse_id'].nunique()}"
    )

    print(
        f"Snapshot Dates: "
        f"{inventory_df['snapshot_date'].nunique()}"
    )

    print("\n=== CAPACITY VALIDATION ===")

    warehouse_totals = (
        inventory_df.groupby(
            ["warehouse_id", "snapshot_date"]
        )["quantity_on_hand"]
        .sum()
        .reset_index(name="total_on_hand")
    )

    warehouse_totals = warehouse_totals.merge(
        warehouses[["warehouse_id", "capacity_units"]],
        on="warehouse_id",
        how="left",
        validate="many_to_one",
    )

    warehouse_totals["utilization_pct"] = (
        warehouse_totals["total_on_hand"]
        / warehouse_totals["capacity_units"]
        * 100
    )

    print(
        warehouse_totals.groupby("warehouse_id")[
            "utilization_pct"
        ].agg(["min", "mean", "max"]).round(2)
    )

    assert (
        warehouse_totals["total_on_hand"]
        <= warehouse_totals["capacity_units"]
    ).all(), "Warehouse capacity exceeded!"

    assert (
        warehouse_totals["utilization_pct"]
        <= MAX_CAPACITY_UTILIZATION * 100
    ).all(), "Operational utilization limit exceeded!"

    print("\nCapacity validation passed.")

    print("\nStockout Records:")
    print(
        (inventory_df["quantity_on_hand"] == 0).sum()
    )

    print("\nInventory Preview:")
    print(inventory_df.head())

    print("\nInventory Data Generation Completed!")


if __name__ == "__main__":
    main()
