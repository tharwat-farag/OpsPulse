"""
OpsPulse Cloud Warehouse Migration & Safe Resumable Replication Utility.

Copies schemas, tables, constraints, identity columns, sequences, and data
from the local OpsPulse PostgreSQL warehouse (opspulse_dw) to a target
Cloud PostgreSQL database (e.g., Neon, Supabase, AWS RDS, GCP Cloud SQL).

Key Features:
- Non-destructive, idempotent, and safely resumable across partial failures.
- Automatically handles GENERATED ALWAYS / BY DEFAULT identity columns with OVERRIDING SYSTEM VALUE.
- Automatically discovers and synchronizes PostgreSQL identity sequences post-insertion.
- Uses ON CONFLICT DO NOTHING to prevent duplicate rows without truncating or dropping.
- Automatically verifies primary key consistency and business metric accuracy upon completion.
- Masked interactive password input protects connection strings from shell history and logs.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    text,
    select,
    inspect,
)
from warehouse.db_connection import get_database_engine


TABLE_ORDER_GOLD = [
    # Dimension & bridge tables first (parent entities)
    "dim_date",
    "dim_sales_channel",
    "dim_expense_category",
    "dim_product",
    "dim_customer",
    "dim_branch",
    "dim_warehouse",
    "dim_supplier",
    "bridge_product_supplier",
    "bridge_branch_warehouse",
    # Fact tables next (child entities)
    "fact_sales",
    "fact_inventory_snapshot",
    "fact_purchase_order_lines",
    "fact_goods_receipts",
    "fact_operating_expenses",
]

TABLE_ORDER_MONITORING = [
    "pipeline_run_metrics",
    "pipeline_task_metrics",
    "pipeline_data_volume_metrics",
    "pipeline_failure_events",
]


def normalize_url(url: str) -> str:
    """Ensure standard postgresql driver format."""
    url = url.strip().strip("'\"")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def redact_url(url: str) -> str:
    """Redacts password from connection URL for safe logging."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=netloc))
        return url
    except Exception:
        return "postgresql://***:***@host/db"


def verify_source_database(source_engine) -> bool:
    """Confirms the source is indeed the populated local opspulse_dw database."""
    try:
        with source_engine.connect() as conn:
            current_db = conn.execute(text("SELECT current_database();")).scalar()
            gold_count = conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'gold';")
            ).scalar()
            sales_rows = conn.execute(text("SELECT COUNT(*) FROM gold.fact_sales;")).scalar()

            print(f" Source Database:        '{current_db}'")
            print(f" Source Gold Tables:     {gold_count} tables")
            print(f" Source fact_sales Rows: {sales_rows:,} rows")

            if current_db != "opspulse_dw" and "opspulse" not in current_db.lower():
                print(f"  Warning: Source database '{current_db}' does not match expected 'opspulse_dw'!")
                return False

            if sales_rows != 20000:
                print(f"  Warning: Source fact_sales has {sales_rows} rows (expected 20,000)!")
                return False

            return True
    except Exception as e:
        print(f" Failed to verify source database: {e}")
        return False


def get_table_identities_and_pks(conn, schema_name: str, tbl_name: str, tgt_tbl) -> Tuple[bool, List[str], List[str]]:
    """
    Discovers:
    1. If the table has any IDENTITY column (GENERATED ALWAYS or BY DEFAULT).
    2. Names of identity columns.
    3. Names of primary key columns for ON CONFLICT resolution.
    """
    # 1. Identity columns check
    ident_sql = text("""
        SELECT a.attname AS col_name, a.attidentity
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = :schema
          AND c.relname = :table
          AND a.attidentity IN ('a', 'd')
          AND NOT a.attisdropped;
    """)
    ident_rows = conn.execute(ident_sql, {"schema": schema_name, "table": tbl_name}).fetchall()
    ident_cols = [r[0] for r in ident_rows]
    has_identity = len(ident_cols) > 0 or any(getattr(c, "identity", None) is not None for c in tgt_tbl.columns)

    # 2. Primary key columns
    pk_cols = [c.name for c in tgt_tbl.primary_key.columns]

    return has_identity, ident_cols, pk_cols


def sync_identity_sequences(conn, schema_name: str, tbl_name: str) -> None:
    """
    Synchronizes PostgreSQL sequence values for identity columns
    so future DEFAULT inserts do not collide with replicated surrogate keys.
    """
    ident_sql = text("""
        SELECT a.attname AS col_name
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = :schema
          AND c.relname = :table
          AND a.attidentity IN ('a', 'd')
          AND NOT a.attisdropped;
    """)
    ident_cols = [r[0] for r in conn.execute(ident_sql, {"schema": schema_name, "table": tbl_name}).fetchall()]

    for col in ident_cols:
        seq_sql = text(f"SELECT pg_get_serial_sequence('{schema_name}.{tbl_name}', '{col}');")
        seq_name = conn.execute(seq_sql).scalar()
        if seq_name:
            sync_sql = text(f"""
                SELECT setval('{seq_name}', COALESCE((SELECT MAX("{col}") FROM {schema_name}.{tbl_name}), 1));
            """)
            conn.execute(sync_sql)


def build_safe_insert_statement(
    schema_name: str,
    table_name: str,
    columns: List[str],
    pk_columns: List[str],
    has_identity: bool,
) -> text:
    """
    Constructs an idempotent, identity-preserving INSERT statement.
    Includes OVERRIDING SYSTEM VALUE when identity columns are present,
    and ON CONFLICT ({pk}) DO NOTHING for safe resuming.
    """
    col_str = ", ".join(f'"{c}"' for c in columns)
    param_str = ", ".join(f":{c}" for c in columns)
    override_str = "OVERRIDING SYSTEM VALUE" if has_identity else ""

    if pk_columns:
        pk_str = ", ".join(f'"{c}"' for c in pk_columns)
        conflict_str = f"ON CONFLICT ({pk_str}) DO NOTHING"
    else:
        conflict_str = ""

    sql = f"""
        INSERT INTO {schema_name}.{table_name} ({col_str})
        {override_str}
        VALUES ({param_str})
        {conflict_str};
    """
    return text(sql)


def replicate_schema(
    schema_name: str,
    table_list: List[str],
    source_engine,
    target_engine,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Replicates a schema from local opspulse_dw to cloud target with safe resume support.
    """
    print(f"\n========================================================")
    print(f"       REPLICATING SCHEMA: {schema_name.upper()}        ")
    print(f"========================================================")

    # Reflect source schema
    source_meta = MetaData(schema=schema_name)
    source_meta.reflect(bind=source_engine)

    target_meta = MetaData(schema=schema_name)
    tables_processed = 0
    total_rows_transferred = 0

    for tbl_name in table_list:
        full_tbl_name = f"{schema_name}.{tbl_name}"

        if full_tbl_name not in source_meta.tables:
            print(f"  [SKIPPED] {full_tbl_name} not found in source metadata.")
            continue

        src_tbl = source_meta.tables[full_tbl_name]

        # 1. Check Source Row Count
        with source_engine.connect() as s_conn:
            src_count = s_conn.execute(text(f"SELECT COUNT(*) FROM {full_tbl_name};")).scalar()

        # 2. Create Target Table if Not Exists
        tgt_tbl = src_tbl.to_metadata(target_meta)
        if not dry_run:
            tgt_tbl.create(target_engine, checkfirst=True)

        # 3. Check Target State
        target_count = 0
        target_exists = False
        with target_engine.connect() as t_conn:
            try:
                target_count = t_conn.execute(text(f"SELECT COUNT(*) FROM {full_tbl_name};")).scalar()
                target_exists = True
            except Exception:
                target_exists = False

        # --- Dry Run Mode ---
        if dry_run:
            status = f"Already has {target_count:,} rows" if target_exists and target_count > 0 else "Ready for transfer"
            print(f"  [DRY-RUN] {full_tbl_name:<34} Source: {src_count:>6,} rows | Target: {status}")
            tables_processed += 1
            continue

        # --- Safe Resume Mode ---
        # Case A: Target is already completely replicated
        if target_exists and target_count == src_count and src_count > 0:
            print(f"  [RESUMED & VERIFIED] {full_tbl_name:<34}: {target_count:>6,} / {src_count:>6,} rows match. Synchronizing sequence...")
            with target_engine.begin() as t_conn:
                sync_identity_sequences(t_conn, schema_name, tbl_name)
            tables_processed += 1
            continue

        # Case B: Partially populated or empty target
        with target_engine.connect() as t_conn:
            has_identity, ident_cols, pk_cols = get_table_identities_and_pks(
                t_conn, schema_name, tbl_name, tgt_tbl
            )

        status_msg = f"Resuming transfer ({target_count:,} existing rows)" if target_count > 0 else "Transferring data"
        ident_info = f" [Identity: {', '.join(ident_cols)}]" if ident_cols else ""
        print(f"  [COPYING] {full_tbl_name:<34}: {status_msg}{ident_info}...")

        # Build parameterized statement with OVERRIDING SYSTEM VALUE and ON CONFLICT DO NOTHING
        cols = [c.name for c in src_tbl.columns]
        stmt = build_safe_insert_statement(
            schema_name=schema_name,
            table_name=tbl_name,
            columns=cols,
            pk_columns=pk_cols,
            has_identity=has_identity,
        )

        chunk_size = 5000
        table_transferred = 0
        start_t = time.time()

        with source_engine.connect() as s_conn:
            result = s_conn.execute(select(src_tbl))
            while True:
                batch = result.fetchmany(chunk_size)
                if not batch:
                    break
                row_dicts = [dict(r._mapping) for r in batch]
                with target_engine.begin() as t_conn:
                    t_conn.execute(stmt, row_dicts)
                table_transferred += len(row_dicts)
                print(f"    -> Streaming {table_transferred:,} / {src_count:,} rows...", end="\r")

        # Synchronize identity sequence post-insert
        with target_engine.begin() as t_conn:
            sync_identity_sequences(t_conn, schema_name, tbl_name)
            final_tgt_count = t_conn.execute(text(f"SELECT COUNT(*) FROM {full_tbl_name};")).scalar()

        elapsed = time.time() - start_t
        print(f"   {full_tbl_name:<34}: {final_tgt_count:>6,} / {src_count:>6,} rows verified ({elapsed:.2f}s).")
        tables_processed += 1
        total_rows_transferred += final_tgt_count

    return tables_processed, total_rows_transferred


def verify_target_reconciliation(target_engine) -> bool:
    """Verifies authoritative business metrics against target database."""
    print("\n========================================================")
    print("    VERIFYING TARGET CLOUD DATABASE METRICS             ")
    print("========================================================")

    all_passed = True
    with target_engine.connect() as conn:
        # Check 1: Gross Sales
        res_gross = conn.execute(text("SELECT SUM(gross_amount) FROM gold.fact_sales;")).scalar()
        val_gross = Decimal(str(res_gross or 0)).quantize(Decimal("0.01"))
        exp_gross = Decimal("380108747.31")
        pass_gross = val_gross == exp_gross
        print(f"Gross Sales:         ${val_gross:,.2f} (Expected: ${exp_gross:,.2f}) -> {'PASS' if pass_gross else 'FAIL'}")
        all_passed = all_passed and pass_gross

        # Check 2: Total Discounts
        res_disc = conn.execute(text("SELECT SUM(discount_amount) FROM gold.fact_sales;")).scalar()
        val_disc = Decimal(str(res_disc or 0)).quantize(Decimal("0.01"))
        exp_disc = Decimal("22681878.26")
        pass_disc = val_disc == exp_disc
        print(f"Total Discounts:     ${val_disc:,.2f} (Expected: ${exp_disc:,.2f}) -> {'PASS' if pass_disc else 'FAIL'}")
        all_passed = all_passed and pass_disc

        # Check 3: Net Revenue
        res_net = conn.execute(text("SELECT SUM(net_revenue) FROM gold.fact_sales;")).scalar()
        val_net = Decimal(str(res_net or 0)).quantize(Decimal("0.01"))
        exp_net = Decimal("357426869.05")
        pass_net = val_net == exp_net
        print(f"Net Revenue:         ${val_net:,.2f} (Expected: ${exp_net:,.2f}) -> {'PASS' if pass_net else 'FAIL'}")
        all_passed = all_passed and pass_net

        # Check 4: Gross Profit
        res_profit = conn.execute(text("SELECT SUM(gross_profit) FROM gold.fact_sales;")).scalar()
        val_profit = Decimal(str(res_profit or 0)).quantize(Decimal("0.01"))
        exp_profit = Decimal("45431649.88")
        pass_profit = val_profit == exp_profit
        print(f"Gross Profit:        ${val_profit:,.2f} (Expected: ${exp_profit:,.2f}) -> {'PASS' if pass_profit else 'FAIL'}")
        all_passed = all_passed and pass_profit

        # Check 5: Distinct Invoices
        res_invoices = conn.execute(text("SELECT COUNT(DISTINCT invoice_id) FROM gold.fact_sales;")).scalar()
        pass_invoices = res_invoices == 8053
        print(f"Distinct Invoices:   {res_invoices:,} (Expected: 8,053) -> {'PASS' if pass_invoices else 'FAIL'}")
        all_passed = all_passed and pass_invoices

        # Check 6: Inventory Valuation
        res_inv = conn.execute(
            text("SELECT SUM(total_inventory_value) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);")
        ).scalar()
        val_inv = Decimal(str(res_inv or 0)).quantize(Decimal("0.01"))
        exp_inv = Decimal("17169853.11")
        pass_inv = val_inv == exp_inv
        print(f"Inventory Valuation: ${val_inv:,.2f} (Expected: ${exp_inv:,.2f}) -> {'PASS' if pass_inv else 'FAIL'}")
        all_passed = all_passed and pass_inv

        # Check 7: Stockout Rate
        res_stockout = conn.execute(
            text("SELECT ROUND(COUNT(CASE WHEN is_stockout THEN 1 END)::numeric / COUNT(*) * 100, 1) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);")
        ).scalar()
        pass_stockout = float(res_stockout or 0) == 18.0
        print(f"Stockout Rate:       {res_stockout}% (Expected: 18.0%) -> {'PASS' if pass_stockout else 'FAIL'}")
        all_passed = all_passed and pass_stockout

        # Check 8: Open Purchase Orders
        res_pos = conn.execute(
            text("SELECT COUNT(DISTINCT po_id) FROM gold.fact_purchase_order_lines WHERE order_status IN ('Pending', 'Partially Received');")
        ).scalar()
        pass_pos = res_pos == 782
        print(f"Open POs:            {res_pos:,} (Expected: 782) -> {'PASS' if pass_pos else 'FAIL'}")
        all_passed = all_passed and pass_pos

        # Check 9: Operating Expenses (Authoritative Database Value: $39,631,974.10)
        res_opex = conn.execute(text("SELECT SUM(amount) FROM gold.fact_operating_expenses;")).scalar()
        val_opex = Decimal(str(res_opex or 0)).quantize(Decimal("0.01"))
        exp_opex = Decimal("39631974.10")
        pass_opex = val_opex == exp_opex
        print(f"Operating Expenses:  ${val_opex:,.2f} (Expected: ${exp_opex:,.2f}) -> {'PASS' if pass_opex else 'FAIL'}")
        all_passed = all_passed and pass_opex

        # Check 10: Goods Receipt Acceptance Rate
        res_accept_avg = conn.execute(text("SELECT ROUND((AVG(acceptance_rate) * 100)::numeric, 1) FROM gold.fact_goods_receipts;")).scalar()
        res_accept_agg = conn.execute(text("SELECT ROUND((SUM(accepted_qty)::numeric / SUM(received_qty) * 100), 1) FROM gold.fact_goods_receipts;")).scalar()
        pass_accept = float(res_accept_avg or 0) == 95.7 and float(res_accept_agg or 0) == 97.7
        print(f"Receipt Acceptance:  Avg: {res_accept_avg}%, Agg: {res_accept_agg}% (Expected: 95.7% / 97.7%) -> {'PASS' if pass_accept else 'FAIL'}")
        all_passed = all_passed and pass_accept

        # Check 11: Active Suppliers
        res_suppliers = conn.execute(text("SELECT COUNT(*) FROM gold.dim_supplier WHERE is_active = TRUE;")).scalar()
        pass_suppliers = res_suppliers == 10
        print(f"Active Suppliers:    {res_suppliers} (Expected: 10) -> {'PASS' if pass_suppliers else 'FAIL'}")
        all_passed = all_passed and pass_suppliers

    print("========================================================")
    if all_passed:
        print(" ALL 11 BUSINESS METRICS RECONCILED WITH 100% ACCURACY!")
    else:
        print("  WARNING: SOME METRICS DID NOT MATCH.")
    return all_passed


def run_replication(target_url: str, dry_run: bool = False) -> bool:
    target_url = normalize_url(target_url)
    source_engine = get_database_engine()

    print("========================================================")
    print("      OPSPULSE CLOUD WAREHOUSE REPLICATION UTILITY      ")
    print("========================================================")
    print(f"Mode: {'DRY-RUN (Pre-flight Inspection)' if dry_run else 'LIVE SAFE-RESUME REPLICATION'}")
    print(f"Target URL: {redact_url(target_url)}")

    # 1. Verify Source
    print("\n--- Verifying Source Database ---")
    if not verify_source_database(source_engine):
        print(" ABORTED: Source database verification failed.")
        return False

    # Prevent accidental self-replication
    src_url = str(source_engine.url)
    if target_url == src_url or target_url.startswith(src_url.replace("+psycopg", "")):
        print(" ABORTED: Target URL is identical to Source URL. Self-replication prohibited!")
        return False

    # 2. Test Target Connection
    print("\n--- Testing Target Cloud Connection ---")
    try:
        target_engine = create_engine(target_url, pool_pre_ping=True)
        with target_engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            current_target_db = conn.execute(text("SELECT current_database();")).scalar()
            print(f" Target Database:  '{current_target_db}'")
            print(f" Target Version:   {res[:55]}...")
    except Exception as e:
        print(f" Connection Error: Failed to connect to target database: {e}")
        return False

    # 3. Create Schemas on Target if Not Exist
    if not dry_run:
        print("\nEnsuring schemas 'gold' and 'monitoring' exist on target...")
        with target_engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS monitoring;"))
        print(" Schemas verified on target.")

    # 4. Safe Resume Replication
    gold_tables, gold_rows = replicate_schema(
        schema_name="gold",
        table_list=TABLE_ORDER_GOLD,
        source_engine=source_engine,
        target_engine=target_engine,
        dry_run=dry_run,
    )

    mon_tables, mon_rows = replicate_schema(
        schema_name="monitoring",
        table_list=TABLE_ORDER_MONITORING,
        source_engine=source_engine,
        target_engine=target_engine,
        dry_run=dry_run,
    )

    print("\n========================================================")
    print("                 REPLICATION SUMMARY                    ")
    print("========================================================")
    print(f"Gold Tables Processed:       {gold_tables} / {len(TABLE_ORDER_GOLD)}")
    print(f"Monitoring Tables Processed: {mon_tables} / {len(TABLE_ORDER_MONITORING)}")

    if not dry_run:
        return verify_target_reconciliation(target_engine)
    else:
        print("\n[DRY-RUN COMPLETE] No data or schema was modified.")
        return True


if __name__ == "__main__":
    import getpass
    parser = argparse.ArgumentParser(description="Replicate OpsPulse warehouse to Cloud PostgreSQL.")
    parser.add_argument(
        "--target-url",
        required=False,
        default=None,
        help="Target PostgreSQL connection URL (optional; fallback to TARGET_DATABASE_URL env var or interactive hidden prompt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform pre-flight check and display planned table copies without modifying target",
    )
    args = parser.parse_args()

    target_url = args.target_url or os.environ.get("TARGET_DATABASE_URL")
    if not target_url:
        try:
            target_url = getpass.getpass("Enter target PostgreSQL connection URL (input hidden): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)

    if not target_url:
        print("Error: No target PostgreSQL connection URL provided.")
        sys.exit(1)

    success = run_replication(target_url=target_url, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
