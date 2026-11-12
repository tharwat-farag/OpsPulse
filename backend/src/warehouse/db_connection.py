
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_engine() -> Engine:
    """
    Create a SQLAlchemy engine for the OpsPulse warehouse.
    """

    database_url = os.getenv("OPSPULSE_DATABASE_URL")

    if not database_url:
        raise ValueError(
            "OPSPULSE_DATABASE_URL environment variable is not set."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )

    return engine
