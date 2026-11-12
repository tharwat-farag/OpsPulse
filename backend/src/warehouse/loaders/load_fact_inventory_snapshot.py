
from pathlib import Path
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "inventory.csv"
)

STAGING_TABLE = "stg_inventory_snapshot"
CHUNK_SIZE = 1000


REQUIRED_COLUMNS = [
    "inventory_snapshot_id",
    "product_id",
    "warehouse_id",
    "snapshot_date",
    "quantity_on_hand",
    "quantity_reserved",
    "standard_cost",
    "capacity_units",
    "available_quantity",
    "is_stockout",
    "is_fully_reserved",
    "is_reserved_exceeds_on_hand",
    "total_inventory_value",
    "available_inventory_value",
    "reserved_inventory_value",
    "warehouse_total_on_hand",
    "capacity_utilization_pct",
]


# =========================================================
# 1. READ SOURCE DATA
# =========================================================

def read_inventory_data() -> pd.DataFrame:

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Inventory source file not found: {SOURCE_FILE}"
        )

    df = pd.read_csv(
        SOURCE_FILE,
        parse_dates=["snapshot_date"],
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError("Inventory source file is empty.")

    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise ValueError(
            "Inventory source contains NULL values."
        )

    if df["inventory_snapshot_id"].duplicated().any():
        raise ValueError(
            "Duplicate inventory_snapshot_id values found."
        )

    if (
        df.duplicated(
            subset=[
                "product_id",
                "warehouse_id",
                "snapshot_date",
            ]
        ).any()
    ):
        raise ValueError(
            "Duplicate inventory grain detected in Silver."
        )

    if (df["quantity_on_hand"] < 0).any():
        raise ValueError("Negative quantity_on_hand detected.")

    if (df["quantity_reserved"] < 0).any():
        raise ValueError("Negative quantity_reserved detected.")

    if (df["quantity_reserved"] > df["quantity_on_hand"]).any():
        raise ValueError(
            "Reserved quantity exceeds on-hand quantity."
        )

    if (df["available_quantity"] < 0).any():
        raise ValueError("Negative available quantity detected.")

    if (df["standard_cost"] < 0).any():
        raise ValueError("Negative standard cost detected.")

    if (df["capacity_units"] <= 0).any():
        raise ValueError("Invalid warehouse capacity detected.")

    print(f"Silver records read: {len(df):,}")
    print("Source validation: PASSED")

    return df


# =========================================================
# 2. LOAD STAGING
# =========================================================

def load_to_staging(engine, df: pd.DataFrame) -> None:

    print("\nLoading data into Staging...")

    with engine.begin() as connection:

        df[REQUIRED_COLUMNS].to_sql(
            name=STAGING_TABLE,
            schema="staging",
            con=connection,
            if_exists="replace",
            index=False,
            chunksize=CHUNK_SIZE,
            method="multi",
        )

    print("Staging load: COMPLETED")


# =========================================================
# 3. VALIDATE DIMENSION MATCHES
# =========================================================

def validate_dimension_matches(engine) -> None:

    validation_sql = text("""
        SELECT
            COUNT(*) AS source_rows,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_date d
                    WHERE d.full_date = s.snapshot_date::date
                ) <> 1
            ) AS invalid_dates,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_product p
                    WHERE p.product_id = s.product_id
                      AND p.valid_from <= s.snapshot_date::date
                      AND s.snapshot_date::date < p.valid_to
                ) <> 1
            ) AS invalid_products,

            COUNT(*) FILTER (
                WHERE (
                    SELECT COUNT(*)
                    FROM gold.dim_warehouse w
                    WHERE w.warehouse_id = s.warehouse_id
                      AND w.valid_from <= s.snapshot_date::date
                      AND s.snapshot_date::date < w.valid_to
                ) <> 1
            ) AS invalid_warehouses

        FROM staging.stg_inventory_snapshot s;
    """)

    with engine.connect() as connection:
        result = connection.execute(
            validation_sql
        ).mappings().one()

    print("\nDimension matching validation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    invalid_total = (
        result["invalid_dates"]
        + result["invalid_products"]
        + result["invalid_warehouses"]
    )

    if invalid_total > 0:
        raise ValueError(
            "Dimension matching failed."
        )

    print("Dimension matching: PASSED")


# =========================================================
# 4. LOAD FACT INVENTORY SNAPSHOT
# =========================================================

def load_fact_inventory(engine) -> None:

    insert_sql = text("""
        INSERT INTO gold.fact_inventory_snapshot (

            inventory_snapshot_id,

            date_key,
            product_key,
            warehouse_key,

            quantity_on_hand,
            quantity_reserved,
            available_quantity,

            standard_cost,

            total_inventory_value,
            available_inventory_value,
            reserved_inventory_value,

            capacity_units,
            warehouse_total_on_hand,
            capacity_utilization_pct,

            is_stockout,
            is_fully_reserved,
            is_reserved_exceeds_on_hand

        )

        SELECT

            s.inventory_snapshot_id,

            d.date_key,
            p.product_key,
            w.warehouse_key,

            s.quantity_on_hand,
            s.quantity_reserved,
            s.available_quantity,

            s.standard_cost,

            s.total_inventory_value,
            s.available_inventory_value,
            s.reserved_inventory_value,

            s.capacity_units,
            s.warehouse_total_on_hand,
            s.capacity_utilization_pct,

            s.is_stockout,
            s.is_fully_reserved,
            s.is_reserved_exceeds_on_hand

        FROM staging.stg_inventory_snapshot s

        INNER JOIN gold.dim_date d
            ON d.full_date = s.snapshot_date::date

        INNER JOIN gold.dim_product p
            ON p.product_id = s.product_id
           AND p.valid_from <= s.snapshot_date::date
           AND s.snapshot_date::date < p.valid_to

        INNER JOIN gold.dim_warehouse w
            ON w.warehouse_id = s.warehouse_id
           AND w.valid_from <= s.snapshot_date::date
           AND s.snapshot_date::date < w.valid_to

        ON CONFLICT (inventory_snapshot_id) DO NOTHING;
    """)

    with engine.begin() as connection:

        before_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_inventory_snapshot
            """)
        ).scalar_one()

        connection.execute(insert_sql)

        after_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.fact_inventory_snapshot
            """)
        ).scalar_one()

    inserted = after_count - before_count

    print("\nFact Inventory Snapshot load:")
    print(f"Records inserted: {inserted:,}")
    print(f"Total records: {after_count:,}")


# =========================================================
# 5. RECONCILIATION
# =========================================================

def reconcile_inventory(
    engine,
    source_count: int
) -> None:

    reconciliation_sql = text("""
        SELECT
            COUNT(*) AS fact_rows,

            COUNT(DISTINCT inventory_snapshot_id)
                AS unique_snapshot_ids,

            COUNT(DISTINCT (
                date_key,
                product_key,
                warehouse_key
            )) AS unique_grains,

            SUM(quantity_on_hand) AS total_quantity_on_hand,

            SUM(quantity_reserved) AS total_quantity_reserved,

            SUM(available_quantity) AS total_available_quantity,

            SUM(total_inventory_value) AS total_inventory_value,

            SUM(available_inventory_value) AS available_inventory_value,

            SUM(reserved_inventory_value) AS reserved_inventory_value,

            COUNT(*) FILTER (
                WHERE is_stockout = TRUE
            ) AS stockout_records

        FROM gold.fact_inventory_snapshot;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value}")

    if result["fact_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: row count mismatch."
        )

    if result["unique_snapshot_ids"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate snapshot IDs."
        )

    if result["unique_grains"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate inventory grain."
        )

    print("Silver-to-Gold reconciliation: PASSED")


# =========================================================
# 6. MAIN
# =========================================================

def main() -> None:

    print("=" * 55)
    print("OPSPULSE - FACT INVENTORY SNAPSHOT LOADER")
    print("=" * 55)

    engine = get_database_engine()

    try:

        df = read_inventory_data()

        load_to_staging(engine, df)

        validate_dimension_matches(engine)

        load_fact_inventory(engine)

        reconcile_inventory(engine, len(df))

        print("\n" + "=" * 55)
        print(
            "FACT INVENTORY SNAPSHOT LOAD "
            "COMPLETED SUCCESSFULLY."
        )
        print("=" * 55)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
