
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import text

from warehouse.db_connection import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]


INSERT_CHANNEL_SQL = text("""
    INSERT INTO gold.dim_sales_channel (
        sales_channel_name
    )
    VALUES (
        :sales_channel_name
    )
    ON CONFLICT (sales_channel_name)
    DO NOTHING
""")


def read_sales_channels(batch_id: str) -> list[dict]:
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id must not be empty.")

    source_file = (
        PROJECT_ROOT
        / "data"
        / "silver"
        / batch_id
        / "sales.csv"
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_file}"
        )

    df = pd.read_csv(source_file)

    if "sales_channel" not in df.columns:
        raise ValueError("sales_channel column is missing.")

    if df["sales_channel"].isna().any():
        raise ValueError("Null sales channel found.")

    normalized_channels = (
        df["sales_channel"]
        .astype(str)
        .str.strip()
    )

    if normalized_channels.empty:
        raise ValueError("No sales channel records found.")

    if normalized_channels.eq("").any():
        raise ValueError("Empty sales channel value found.")

    channels = sorted(normalized_channels.unique().tolist())

    return [
        {"sales_channel_name": channel}
        for channel in channels
    ]


def main(batch_id: str) -> None:
    print("Starting Sales Channel Dimension Load...")
    print(f"Batch ID: {batch_id}")

    channels = read_sales_channels(batch_id)

    print(f"Distinct channels validated: {len(channels)}")

    engine = get_database_engine()

    try:
        with engine.begin() as connection:
            result = connection.execute(
                INSERT_CHANNEL_SQL,
                channels
            )

            inserted_count = result.rowcount

        skipped_count = len(channels) - inserted_count

        print("\nSales Channel Load Summary")
        print("--------------------------")
        print(f"Source channels:  {len(channels)}")
        print(f"Inserted:         {inserted_count}")
        print(f"Skipped:          {skipped_count}")
        print("Load completed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load Sales Channel Dimension from a Silver batch."
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Silver batch ID to load."
    )

    args = parser.parse_args()
    main(args.batch_id)
