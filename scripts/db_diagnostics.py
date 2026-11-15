import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))
from warehouse.db_connection import get_database_engine
from sqlalchemy import text, inspect

engine = get_database_engine()

# Redacted connection info
url = engine.url
host = url.host or "localhost"
port = url.port or 5432
db_name = url.database
driver = url.drivername

print("==================================================")
print("       LOCAL WAREHOUSE READ-ONLY DIAGNOSTICS      ")
print("==================================================")
print(f"Driver:             {driver}")
print(f"Host:               {host}")
print(f"Port:               {port}")
print(f"Database:           {db_name}")
print(f"User:               {url.username}")

with engine.connect() as conn:
    current_db = conn.execute(text("SELECT current_database();")).scalar()
    current_user = conn.execute(text("SELECT current_user;")).scalar()
    pg_version = conn.execute(text("SELECT version();")).scalar()
    schemas = [
        r[0]
        for r in conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast');"
            )
        ).fetchall()
    ]

    print(f"Verified Database:  {current_db}")
    print(f"Verified User:      {current_user}")
    print(f"PostgreSQL Ver:     {pg_version[:60]}...")
    print(f"Available Schemas:  {schemas}")

    insp = inspect(engine)
    print("\n--- GOLD SCHEMA TABLES AND ROW COUNTS ---")
    gold_tables = insp.get_table_names(schema="gold")
    total_gold_rows = 0
    for tbl in sorted(gold_tables):
        count = conn.execute(text(f"SELECT COUNT(*) FROM gold.{tbl};")).scalar()
        total_gold_rows += count
        print(f"  gold.{tbl:<28} : {count:>7,} rows")
    print(f"Total Gold Tables: {len(gold_tables)} (Total Rows: {total_gold_rows:,})")

    print("\n--- MONITORING SCHEMA TABLES AND ROW COUNTS ---")
    mon_tables = insp.get_table_names(schema="monitoring")
    total_mon_rows = 0
    for tbl in sorted(mon_tables):
        count = conn.execute(text(f"SELECT COUNT(*) FROM monitoring.{tbl};")).scalar()
        total_mon_rows += count
        print(f"  monitoring.{tbl:<22} : {count:>7,} rows")
    print(f"Total Monitoring Tables: {len(mon_tables)} (Total Rows: {total_mon_rows:,})")

    print("\n--- FACT_SALES CHECK ---")
    sales_count = conn.execute(text("SELECT COUNT(*) FROM gold.fact_sales;")).scalar()
    print(f"  gold.fact_sales exact count : {sales_count:,} rows")
print("==================================================")
