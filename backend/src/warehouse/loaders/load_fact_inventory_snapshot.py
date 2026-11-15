
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STAGING_TABLE = "stg_inventory_snapshot"
CHUNK_SIZE = 100

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

def read_inventory_data(batch_id: str) -> pd.DataFrame:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "inventory.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Inventory source file not found: {source_file}"
        )

    df = pd.read_csv(
        source_file,
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

    if df.duplicated(
        subset=[
            "product_id",
            "warehouse_id",
            "snapshot_date",
        ]
    ).any():
        raise ValueError(
            "Duplicate inventory grain detected in Silver."
        )

    if (df["quantity_on_hand"] < 0).any():
        raise ValueError(
            "Negative quantity_on_hand detected."
        )

    if (df["quantity_reserved"] < 0).any():
        raise ValueError(
            "Negative quantity_reserved detected."
        )

    if (
        df["quantity_reserved"] > df["quantity_on_hand"]
    ).any():
        raise ValueError(
            "Reserved quantity exceeds on-hand quantity."
        )

    if (df["available_quantity"] < 0).any():
        raise ValueError(
            "Negative available quantity detected."
        )

    if (df["standard_cost"] < 0).any():
        raise ValueError(
            "Negative standard cost detected."
        )

    if (df["capacity_units"] <= 0).any():
        raise ValueError(
            "Invalid warehouse capacity detected."
        )

    print(f"Silver records read: {len(df):,}")
    print("Source validation: PASSED")

    return df


# =========================================================
# 2. LOAD STAGING
# =========================================================

def load_to_staging(
    engine,
    df: pd.DataFrame,
) -> None:

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
    print(f"Total records in Gold: {after_count:,}")


# =========================================================
# 5. RECONCILIATION
# =========================================================

def reconcile_inventory(
    engine,
    source_count: int,
) -> None:

    reconciliation_sql = text("""
        SELECT

            COUNT(*) AS source_rows,

            COUNT(DISTINCT s.inventory_snapshot_id)
                AS unique_source_ids,

            COUNT(DISTINCT f.inventory_snapshot_id)
                AS unique_fact_ids,

            COUNT(DISTINCT (
                f.date_key,
                f.product_key,
                f.warehouse_key
            )) AS unique_fact_grains,

            COUNT(*) FILTER (
                WHERE
                    f.inventory_snapshot_id IS NULL

                    OR f.date_key IS DISTINCT FROM d.date_key

                    OR f.product_key IS DISTINCT FROM p.product_key

                    OR f.warehouse_key IS DISTINCT FROM w.warehouse_key

                    OR f.quantity_on_hand IS DISTINCT FROM s.quantity_on_hand

                    OR f.quantity_reserved IS DISTINCT FROM s.quantity_reserved

                    OR f.available_quantity IS DISTINCT FROM s.available_quantity

                    OR ABS(
                        f.standard_cost - s.standard_cost
                    ) > 0.000001

                    OR ABS(
                        f.total_inventory_value - s.total_inventory_value
                    ) > 0.000001

                    OR ABS(
                        f.available_inventory_value - s.available_inventory_value
                    ) > 0.000001

                    OR ABS(
                        f.reserved_inventory_value - s.reserved_inventory_value
                    ) > 0.000001

                    OR f.capacity_units IS DISTINCT FROM s.capacity_units

                    OR f.warehouse_total_on_hand
                        IS DISTINCT FROM s.warehouse_total_on_hand

                    OR ABS(
                        f.capacity_utilization_pct
                        - s.capacity_utilization_pct
                    ) > 0.00005

                    OR f.is_stockout IS DISTINCT FROM s.is_stockout

                    OR f.is_fully_reserved
                        IS DISTINCT FROM s.is_fully_reserved

                    OR f.is_reserved_exceeds_on_hand
                        IS DISTINCT FROM s.is_reserved_exceeds_on_hand

            ) AS mismatched_rows

        FROM staging.stg_inventory_snapshot s

        LEFT JOIN gold.fact_inventory_snapshot f
            ON f.inventory_snapshot_id = s.inventory_snapshot_id

        LEFT JOIN gold.dim_date d
            ON d.full_date = s.snapshot_date::date

        LEFT JOIN gold.dim_product p
            ON p.product_id = s.product_id
           AND p.valid_from <= s.snapshot_date::date
           AND s.snapshot_date::date < p.valid_to

        LEFT JOIN gold.dim_warehouse w
            ON w.warehouse_id = s.warehouse_id
           AND w.valid_from <= s.snapshot_date::date
           AND s.snapshot_date::date < w.valid_to;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            reconciliation_sql
        ).mappings().one()

    print("\nSilver-to-Gold reconciliation:")

    for key, value in result.items():
        print(f"{key}: {value:,}")

    if result["source_rows"] != source_count:
        raise ValueError(
            "Reconciliation failed: source row count mismatch."
        )

    if result["unique_source_ids"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate source snapshot IDs."
        )

    if result["unique_fact_ids"] != source_count:
        raise ValueError(
            "Reconciliation failed: missing fact snapshot IDs."
        )

    if result["unique_fact_grains"] != source_count:
        raise ValueError(
            "Reconciliation failed: duplicate fact inventory grain."
        )

    if result["mismatched_rows"] != 0:
        raise ValueError(
            "Reconciliation failed: source and fact values do not match."
        )

    print("Silver-to-Gold reconciliation: PASSED")


# =========================================================
# 6. MAIN
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError("A valid batch_id is required.")

    print("=" * 55)
    print("OPSPULSE - FACT INVENTORY SNAPSHOT LOADER")
    print(f"Batch ID: {batch_id}")
    print("=" * 55)

    engine = get_database_engine()

    try:

        df = read_inventory_data(batch_id)

        load_to_staging(engine, df)

        validate_dimension_matches(engine)

        load_fact_inventory(engine)

        reconcile_inventory(
            engine,
            len(df),
        )

        print("\n" + "=" * 55)
        print(
            "FACT INVENTORY SNAPSHOT LOAD "
            "COMPLETED SUCCESSFULLY."
        )
        print("=" * 55)

    finally:
        engine.dispose()


# =========================================================
# 7. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Inventory Snapshot data into Gold."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
