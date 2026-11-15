
import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from warehouse.db_connection import get_database_engine


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

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


# =========================================================
# 1. PARSE BOOLEAN
# =========================================================

def parse_boolean(value: str) -> bool:

    normalized_value = value.strip().lower()

    if normalized_value == "true":
        return True

    if normalized_value == "false":
        return False

    raise ValueError(
        f"Invalid boolean value: {value}"
    )


# =========================================================
# 2. READ AND VALIDATE BRANCHES
# =========================================================

def read_branches(batch_id: str) -> list[dict]:

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "branches.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    with source_file.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        source_columns = set(reader.fieldnames or [])

        missing_columns = (
            REQUIRED_COLUMNS - source_columns
        )

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        branches = list(reader)

    if not branches:
        raise ValueError(
            "Source file contains no branches."
        )

    records = []
    branch_ids = set()

    for row in branches:

        branch_id = row["branch_id"].strip()

        if not branch_id:
            raise ValueError(
                "Empty branch_id found."
            )

        if branch_id in branch_ids:
            raise ValueError(
                f"Duplicate branch_id found: {branch_id}"
            )

        branch_ids.add(branch_id)

        branch_name = row["branch_name"].strip()
        city = row["city"].strip()
        region = row["region"].strip()
        manager_name = row["manager_name"].strip()

        if any(
            not value
            for value in [
                branch_name,
                city,
                region,
                manager_name,
            ]
        ):
            raise ValueError(
                f"Missing required value in branch: {branch_id}"
            )

        try:
            opening_date = date.fromisoformat(
                row["opening_date"].strip()
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid opening_date for branch {branch_id}."
            ) from exc

        is_active = parse_boolean(
            row["is_active"]
        )

        records.append({
            "branch_id": branch_id,
            "branch_name": branch_name,
            "city": city,
            "region": region,
            "manager_name": manager_name,
            "opening_date": opening_date,
            "is_active": is_active,
            "valid_from": BASELINE_DATE,
        })

    print(f"Source records validated: {len(records):,}")
    print("Branch source validation: PASSED")

    return records


# =========================================================
# 3. LOAD BRANCH DIMENSION
# =========================================================

def load_branches(branches: list[dict]) -> None:

    print("\nLoading Branch Dimension...")

    engine = get_database_engine()

    try:

        with engine.begin() as connection:

            result = connection.execute(
                INSERT_BRANCH_SQL,
                branches,
            )

            inserted_count = result.rowcount

        skipped_count = len(branches) - inserted_count

        print("\nBranch Dimension Load Summary")
        print("--------------------------------")
        print(f"Source records:   {len(branches):,}")
        print(f"Inserted records: {inserted_count:,}")
        print(f"Skipped records:  {skipped_count:,}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


# =========================================================
# 4. MAIN EXECUTION
# =========================================================

def main(batch_id: str) -> None:

    if not batch_id or not batch_id.strip():
        raise ValueError(
            "A valid batch_id is required."
        )

    print("=" * 55)
    print("OPSPULSE - BRANCH DIMENSION INITIAL LOAD")
    print(f"Batch ID: {batch_id}")
    print("=" * 55)

    branches = read_branches(batch_id)

    load_branches(branches)

    print("\nBranch Dimension Initial Load completed.")


# =========================================================
# 5. COMMAND LINE EXECUTION
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Load Branch Dimension baseline data."
    )

    parser.add_argument(
        "batch_id",
        type=str,
        help="Silver batch ID to process.",
    )

    args = parser.parse_args()

    main(args.batch_id)
