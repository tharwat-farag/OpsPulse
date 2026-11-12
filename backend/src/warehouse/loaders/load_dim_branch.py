
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]

BATCH_ID = "batch_20261111_124227_c8e6ab39"

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "silver"
    / BATCH_ID
    / "branches.csv"
)

BASELINE_DATE = date(2025, 1, 1)

REQUIRED_COLUMNS = {
    "branch_id",
    "branch_name",
    "city",
    "region",
    "manager_name",
    "opening_date",
    "is_active",
}


INSERT_BRANCH_SQL = text("""
    INSERT INTO gold.dim_branch (
        branch_id,
        branch_name,
        city,
        region,
        manager_name,
        opening_date,
        is_active,
        valid_from,
        valid_to,
        is_current
    )
    VALUES (
        :branch_id,
        :branch_name,
        :city,
        :region,
        :manager_name,
        :opening_date,
        :is_active,
        :valid_from,
        DATE '9999-12-31',
        TRUE
    )
    ON CONFLICT (branch_id) WHERE is_current = TRUE
    DO NOTHING
""")


def parse_boolean(value: str) -> bool:
    normalized_value = value.strip().lower()

    if normalized_value == "true":
        return True

    if normalized_value == "false":
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def read_branches():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    with SOURCE_FILE.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        source_columns = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - source_columns

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        branches = list(reader)

    if not branches:
        raise ValueError("Source file contains no branches.")

    branch_ids = [
        row["branch_id"].strip()
        for row in branches
    ]

    if len(branch_ids) != len(set(branch_ids)):
        raise ValueError("Duplicate branch_id found in source.")

    records = []

    for row in branches:
        required_values = [
            row["branch_id"],
            row["branch_name"],
            row["city"],
            row["region"],
            row["manager_name"],
        ]

        if any(not value or not value.strip() for value in required_values):
            raise ValueError(
                f"Missing required value in branch: {row['branch_id']}"
            )

        records.append({
            "branch_id": row["branch_id"].strip(),
            "branch_name": row["branch_name"].strip(),
            "city": row["city"].strip(),
            "region": row["region"].strip(),
            "manager_name": row["manager_name"].strip(),
            "opening_date": date.fromisoformat(
                row["opening_date"].strip()
            ),
            "is_active": parse_boolean(row["is_active"]),
            "valid_from": BASELINE_DATE,
        })

    return records


def main():
    print("Starting Branch Dimension Initial Load...")

    branches = read_branches()

    print(f"Source records validated: {len(branches)}")

    engine = get_database_engine()

    with engine.begin() as connection:
        result = connection.execute(
            INSERT_BRANCH_SQL,
            branches
        )

        inserted_count = result.rowcount

    skipped_count = len(branches) - inserted_count

    print("\nBranch Dimension Load Summary")
    print("--------------------------------")
    print(f"Source records:   {len(branches)}")
    print(f"Inserted records: {inserted_count}")
    print(f"Skipped records:  {skipped_count}")
    print("Load completed successfully.")


if __name__ == "__main__":
    main()
