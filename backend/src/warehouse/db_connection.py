
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

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )

    return engine

