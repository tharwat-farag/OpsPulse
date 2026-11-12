
import random
import pandas as pd

from faker import Faker

from config import (
    RANDOM_SEED,
    NUM_BRANCHES,
    NUM_WAREHOUSES,
    RAW_DATA_DIR,
)

# -----------------------------------
# 1. Initialize Random Generators
# -----------------------------------

random.seed(RANDOM_SEED)

fake = Faker("en_US")
fake.seed_instance(RANDOM_SEED)


# -----------------------------------
# 2. Generate Branches
# -----------------------------------

def generate_branches():

    branch_locations = [
        ("Cairo", "Greater Cairo"),
        ("Giza", "Greater Cairo"),
        ("Alexandria", "Alexandria"),
        ("Tanta", "Delta"),
        ("Mansoura", "Delta"),
    ]

    branches = []

    for i in range(NUM_BRANCHES):

        city, region = branch_locations[i]

        branch = {
            "branch_id": f"B{i + 1:03d}",
            "branch_name": f"{city} Branch",
            "city": city,
            "region": region,
            "manager_name": fake.name(),
            "opening_date": fake.date_between(
                start_date="-10y",
                end_date="-1y"
            ),
            "is_active": True,
        }

        branches.append(branch)

    return pd.DataFrame(branches)


# -----------------------------------
# 3. Generate Warehouses
# -----------------------------------

def generate_warehouses():

    warehouse_locations = [
        ("Cairo", "Greater Cairo"),
        ("Giza", "Greater Cairo"),
        ("Alexandria", "Alexandria"),
    ]

    warehouses = []

    for i in range(NUM_WAREHOUSES):

        city, region = warehouse_locations[i]

        warehouse = {
            "warehouse_id": f"W{i + 1:03d}",
            "warehouse_name": f"{city} Main Warehouse",
            "city": city,
            "region": region,
            "capacity_units": random.randint(5000, 15000),
            "is_active": True,
        }

        warehouses.append(warehouse)

    return pd.DataFrame(warehouses)


# -----------------------------------
# 4. Save Data as CSV
# -----------------------------------

def save_dataframe(df, filename):

    output_path = RAW_DATA_DIR / filename

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Saved: {output_path}")
    print(f"Records: {len(df)}")


# -----------------------------------
# 5. Main Execution
# -----------------------------------

def main():

    print("Starting Reference Data Generation...")

    branches_df = generate_branches()
    warehouses_df = generate_warehouses()

    save_dataframe(branches_df, "branches.csv")
    save_dataframe(warehouses_df, "warehouses.csv")

    print("\nReference Data Generation Completed!")


if __name__ == "__main__":
    main()
