
import pandas as pd
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
    / "sales.csv"
)


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


def read_sales_channels():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    df = pd.read_csv(SOURCE_FILE)

    if "sales_channel" not in df.columns:
        raise ValueError("sales_channel column is missing.")

    if df["sales_channel"].isna().any():
        raise ValueError("Null sales channel found.")

    channels = sorted(
        df["sales_channel"].astype(str).str.strip().unique()
    )

    if not channels or any(not channel for channel in channels):
        raise ValueError("Invalid sales channel values.")

    return [
        {"sales_channel_name": channel}
        for channel in channels
    ]


def main():
    print("Starting Sales Channel Dimension Load...")

    channels = read_sales_channels()

    print(f"Distinct channels validated: {len(channels)}")

    engine = get_database_engine()

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


if __name__ == "__main__":
    main()
