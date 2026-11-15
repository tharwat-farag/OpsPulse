"""
OpsPulse Backend API - Database Connection Management.

Provides database dependency injection and connection pooling for analytical queries.
Strictly read-only access to PostgreSQL opspulse_dw.
"""

from typing import Generator
from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
from warehouse.db_connection import get_database_engine

_engine: Engine | None = None


def get_engine() -> Engine:
    """Retrieves or initializes the global SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = get_database_engine()
    return _engine


def get_db_connection() -> Generator[Connection, None, None]:
    """FastAPI dependency for obtaining a database connection."""
    engine = get_engine()
    with engine.connect() as connection:
        yield connection


def check_db_health() -> bool:
    """Verifies active connectivity to PostgreSQL opspulse_dw."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception:
        return False
