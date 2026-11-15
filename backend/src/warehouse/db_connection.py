
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _load_env_if_needed() -> None:
    """Loads environment variables from .env if OPSPULSE_DATABASE_URL is not set."""
    if "OPSPULSE_DATABASE_URL" in os.environ and os.environ["OPSPULSE_DATABASE_URL"]:
        return

    # Check common locations for .env
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for env_file in candidates:
        if env_file.is_file():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                if "OPSPULSE_DATABASE_URL" in os.environ:
                    break
            except Exception:
                pass


def get_database_engine() -> Engine:
    """
    Create a SQLAlchemy engine for the OpsPulse warehouse.
    """
    _load_env_if_needed()
    database_url = os.getenv("OPSPULSE_DATABASE_URL")

    if not database_url:
        raise ValueError(
            "OPSPULSE_DATABASE_URL environment variable is not set."
        )

    # Normalize driver scheme for PostgreSQL (supporting postgres:// and postgresql:// with psycopg3)
    database_url = database_url.strip().strip("'\"")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine_kwargs = {
        "pool_pre_ping": True,
        "future": True,
    }

    # When running on Vercel or in serverless environments, use NullPool to avoid connection leaks
    is_serverless = (
        bool(os.getenv("VERCEL"))
        or bool(os.getenv("SERVERLESS"))
        or os.getenv("OPSPULSE_DB_POOL_TYPE", "").lower() == "null"
    )

    if is_serverless:
        from sqlalchemy.pool import NullPool
        engine_kwargs["poolclass"] = NullPool
    else:
        # Default pooling for long-running servers / local development
        pool_size = int(os.getenv("OPSPULSE_DB_POOL_SIZE", "5"))
        max_overflow = int(os.getenv("OPSPULSE_DB_MAX_OVERFLOW", "10"))
        engine_kwargs["pool_size"] = pool_size
        engine_kwargs["max_overflow"] = max_overflow

    engine = create_engine(
        database_url,
        **engine_kwargs,
    )

    return engine

