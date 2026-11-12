
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


def load_bridge_branch_warehouse():
    engine = get_database_engine()

    with engine.begin() as connection:
        inserted_count = 0

        for branch_id, warehouse_id in BRANCH_WAREHOUSE_MAPPINGS:
            result = connection.execute(
                text("""
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
                      AND w.warehouse_id = :warehouse_id
                    ON CONFLICT DO NOTHING
                    RETURNING branch_warehouse_key
                """),
                {
                    "branch_id": branch_id,
                    "warehouse_id": warehouse_id,
                    "valid_from": MAPPING_BASELINE_DATE,
                },
            )

            inserted_count += len(result.fetchall())

        total_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM gold.bridge_branch_warehouse
                WHERE is_current = TRUE
                  AND is_primary = TRUE
            """)
        ).scalar_one()

        if total_count != len(BRANCH_WAREHOUSE_MAPPINGS):
            raise ValueError(
                "Mapping validation failed: expected "
                f"{len(BRANCH_WAREHOUSE_MAPPINGS)} current primary mappings, "
                f"found {total_count}."
            )

    print("Branch-Warehouse mapping load completed.")
    print(f"Inserted mappings: {inserted_count}")
    print(f"Current primary mappings: {total_count}")


if __name__ == "__main__":
    load_bridge_branch_warehouse()
