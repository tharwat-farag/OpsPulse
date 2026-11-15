"""
OpsPulse Pipeline Observability - Schema Initialization.

Ensures the `monitoring` schema and all monitoring telemetry tables
exist in the PostgreSQL data warehouse.
"""

from pathlib import Path
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "sql" / "create_monitoring_schema.sql"

EXPECTED_TABLES = [
    "pipeline_run_metrics",
    "pipeline_task_metrics",
    "pipeline_data_volume_metrics",
    "pipeline_failure_events",
]


def init_monitoring_schema(engine: Engine) -> None:
    """
    Executes DDL statements to create the `monitoring` schema and its tables.
    Idempotent operation (uses IF NOT EXISTS).
    """
    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"Monitoring schema SQL not found at {SCHEMA_SQL_PATH}")

    sql_statements = SCHEMA_SQL_PATH.read_text(encoding="utf-8")

    with engine.begin() as connection:
        # Split on semicolons or execute statement blocks
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS monitoring;"))
        # Execute DDL
        connection.execute(text(sql_statements))

    # Verify tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names(schema="monitoring"))
    missing = [t for t in EXPECTED_TABLES if t not in existing_tables]

    if missing:
        raise RuntimeError(f"Failed to create monitoring tables: {missing}")

    print("Monitoring schema and tables verified successfully.")
