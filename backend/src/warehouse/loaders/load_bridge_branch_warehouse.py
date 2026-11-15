
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


MAPPING_BASELINE_DATE = "2025-01-01"

BRANCH_WAREHOUSE_MAPPINGS = [
    ("B001", "W001"),
    ("B002", "W002"),
    ("B003", "W003"),
    ("B004", "W001"),
    ("B005", "W002"),
]


INSERT_MAPPING_SQL = text("""
    INSERT INTO gold.bridge_branch_warehouse (
        branch_key,
        warehouse_key,
        is_primary,
        valid_from,
        valid_to,
        is_current
    )
    SELECT
        b.branch_key,
        w.warehouse_key,
        TRUE,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    FROM gold.dim_branch b
    CROSS JOIN gold.dim_warehouse w
    WHERE b.branch_id = :branch_id
      AND b.is_current = TRUE
      AND w.warehouse_id = :warehouse_id
      AND w.is_current = TRUE
    ON CONFLICT DO NOTHING
    RETURNING branch_warehouse_key
""")


VALIDATE_MAPPING_SQL = text("""
    SELECT COUNT(*)
    FROM gold.bridge_branch_warehouse bridge
    JOIN gold.dim_branch branch
        ON bridge.branch_key = branch.branch_key
    JOIN gold.dim_warehouse warehouse
        ON bridge.warehouse_key = warehouse.warehouse_key
    WHERE branch.branch_id = :branch_id
      AND warehouse.warehouse_id = :warehouse_id
      AND bridge.is_primary = TRUE
      AND bridge.is_current = TRUE
      AND branch.is_current = TRUE
      AND warehouse.is_current = TRUE
""")


def load_bridge_branch_warehouse() -> None:
    print("Starting Branch-Warehouse Bridge Load...")

    engine = get_database_engine()

    try:
        inserted_count = 0

        with engine.begin() as connection:

            for branch_id, warehouse_id in BRANCH_WAREHOUSE_MAPPINGS:

                result = connection.execute(
                    INSERT_MAPPING_SQL,
                    {
                        "branch_id": branch_id,
                        "warehouse_id": warehouse_id,
                        "valid_from": MAPPING_BASELINE_DATE,
                    },
                )

                inserted_count += len(result.fetchall())

            invalid_mappings = []

            for branch_id, warehouse_id in BRANCH_WAREHOUSE_MAPPINGS:

                mapping_count = connection.execute(
                    VALIDATE_MAPPING_SQL,
                    {
                        "branch_id": branch_id,
                        "warehouse_id": warehouse_id,
                    },
                ).scalar_one()

                if mapping_count != 1:
                    invalid_mappings.append(
                        f"{branch_id} -> {warehouse_id} "
                        f"(found {mapping_count})"
                    )

            if invalid_mappings:
                raise ValueError(
                    "Branch-Warehouse mapping validation failed:\n"
                    + "\n".join(invalid_mappings)
                )

            total_current_primary = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM gold.bridge_branch_warehouse
                    WHERE is_current = TRUE
                      AND is_primary = TRUE
                """)
            ).scalar_one()

        print("\nBranch-Warehouse Bridge Load Summary")
        print("------------------------------------")
        print(f"Expected mappings:             {len(BRANCH_WAREHOUSE_MAPPINGS)}")
        print(f"Inserted mappings:             {inserted_count}")
        print(f"Current primary mappings total: {total_current_primary}")
        print("All expected mappings validated successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    load_bridge_branch_warehouse()
