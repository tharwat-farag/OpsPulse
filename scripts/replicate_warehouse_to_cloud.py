"""
OpsPulse Cloud Warehouse Migration & Replication Utility.

Copies schemas, tables, constraints, and data from the local OpsPulse
PostgreSQL warehouse (opspulse_dw) to a target Cloud PostgreSQL database
(e.g., Neon, Supabase, Render, AWS RDS).

Usage:
    python scripts/replicate_warehouse_to_cloud.py --target-url "postgresql+psycopg://user:pass@host/dbname?sslmode=require"
"""

import argparse
import os
import sys
import time
from pathlib import Path
from decimal import Decimal

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    text,
    select,
    insert,
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


def migrate_warehouse(target_url: str) -> bool:
    target_url = normalize_url(target_url)
    source_engine = get_database_engine()
    print("Connecting to target cloud PostgreSQL database...")
    target_engine = create_engine(target_url, pool_pre_ping=True)

    # 1. Test target connection
    try:
        with target_engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            print(f" Target connected: {res[:60]}...")
    except Exception as e:
        print(f" Failed to connect to target database: {e}")
        return False

    # 2. Create schemas
    print("\nEnsuring schemas 'gold' and 'monitoring' exist on target...")
    with target_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS monitoring;"))
    print(" Schemas created successfully.")

    # 3. Migrate Gold Tables
    print("\n--- Migrating Gold Schema Tables ---")
    source_meta_gold = MetaData(schema="gold")
    source_meta_gold.reflect(bind=source_engine)

    target_meta_gold = MetaData(schema="gold")

    for tbl_name in TABLE_ORDER_GOLD:
        if tbl_name not in source_meta_gold.tables:
            print(f"  Warning: {tbl_name} not found in source schema, skipping.")
            continue

        src_tbl = source_meta_gold.tables[tbl_name]
        print(f"\nProcessing table: gold.{tbl_name}...")

        # Create target table structure
        src_tbl.tometadata(target_meta_gold)
        tgt_tbl = target_meta_gold.tables[tbl_name]
        tgt_tbl.create(target_engine, checkfirst=True)

        # Clear existing data in target table
        with target_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE gold.{tbl_name} CASCADE;"))

        # Stream records from source to target in chunks
        chunk_size = 5000
        total_rows = 0
        start_time = time.time()

        with source_engine.connect() as s_conn:
            result = s_conn.execute(select(src_tbl))
            while True:
                rows = result.fetchmany(chunk_size)
                if not rows:
                    break
                row_dicts = [dict(r._mapping) for r in rows]
                with target_engine.begin() as t_conn:
                    t_conn.execute(insert(tgt_tbl), row_dicts)
                total_rows += len(row_dicts)
                print(f"  -> Inserted {total_rows} rows...", end="\r")

        elapsed = time.time() - start_time
        print(f"   gold.{tbl_name}: {total_rows} rows copied in {elapsed:.2f}s.")

    # 4. Migrate Monitoring Tables
    print("\n--- Migrating Monitoring Schema Tables ---")
    source_meta_mon = MetaData(schema="monitoring")
    source_meta_mon.reflect(bind=source_engine)

    target_meta_mon = MetaData(schema="monitoring")

    for tbl_name in TABLE_ORDER_MONITORING:
        if tbl_name not in source_meta_mon.tables:
            print(f"  Notice: monitoring.{tbl_name} not found in source schema, skipping.")
            continue

        src_tbl = source_meta_mon.tables[tbl_name]
        print(f"\nProcessing table: monitoring.{tbl_name}...")

        src_tbl.tometadata(target_meta_mon)
        tgt_tbl = target_meta_mon.tables[tbl_name]
        tgt_tbl.create(target_engine, checkfirst=True)

        with target_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE monitoring.{tbl_name} CASCADE;"))

        with source_engine.connect() as s_conn:
            rows = s_conn.execute(select(src_tbl)).fetchall()
            if rows:
                row_dicts = [dict(r._mapping) for r in rows]
                with target_engine.begin() as t_conn:
                    t_conn.execute(insert(tgt_tbl), row_dicts)
                print(f"   monitoring.{tbl_name}: {len(row_dicts)} rows copied.")
            else:
                print(f"   monitoring.{tbl_name}: 0 rows present.")

    # 5. Verification & Reconciliation Queries against Target
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

        # Check 2: Net Revenue
        res_net = conn.execute(text("SELECT SUM(net_revenue) FROM gold.fact_sales;")).scalar()
        val_net = Decimal(str(res_net or 0)).quantize(Decimal("0.01"))
        exp_net = Decimal("357426869.05")
        pass_net = val_net == exp_net
        print(f"Net Revenue:         ${val_net:,.2f} (Expected: ${exp_net:,.2f}) -> {'PASS' if pass_net else 'FAIL'}")
        all_passed = all_passed and pass_net

        # Check 3: Gross Profit
        res_profit = conn.execute(text("SELECT SUM(gross_profit) FROM gold.fact_sales;")).scalar()
        val_profit = Decimal(str(res_profit or 0)).quantize(Decimal("0.01"))
        exp_profit = Decimal("45431649.88")
        pass_profit = val_profit == exp_profit
        print(f"Gross Profit:        ${val_profit:,.2f} (Expected: ${exp_profit:,.2f}) -> {'PASS' if pass_profit else 'FAIL'}")
        all_passed = all_passed and pass_profit

        # Check 4: Distinct Invoices
        res_invoices = conn.execute(text("SELECT COUNT(DISTINCT invoice_id) FROM gold.fact_sales;")).scalar()
        pass_invoices = res_invoices == 8053
        print(f"Distinct Invoices:   {res_invoices:,} (Expected: 8,053) -> {'PASS' if pass_invoices else 'FAIL'}")
        all_passed = all_passed and pass_invoices

        # Check 5: Inventory Valuation
        res_inv = conn.execute(
            text("SELECT SUM(total_inventory_value) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);")
        ).scalar()
        val_inv = Decimal(str(res_inv or 0)).quantize(Decimal("0.01"))
        exp_inv = Decimal("17169853.11")
        pass_inv = val_inv == exp_inv
        print(f"Inventory Valuation: ${val_inv:,.2f} (Expected: ${exp_inv:,.2f}) -> {'PASS' if pass_inv else 'FAIL'}")
        all_passed = all_passed and pass_inv

        # Check 6: Stockout Rate
        res_stockout = conn.execute(
            text("SELECT ROUND(COUNT(CASE WHEN is_stockout THEN 1 END)::numeric / COUNT(*) * 100, 1) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);")
        ).scalar()
        pass_stockout = float(res_stockout or 0) == 18.0
        print(f"Stockout Rate:       {res_stockout}% (Expected: 18.0%) -> {'PASS' if pass_stockout else 'FAIL'}")
        all_passed = all_passed and pass_stockout

        # Check 7: Open Purchase Orders
        res_pos = conn.execute(
            text("SELECT COUNT(DISTINCT po_id) FROM gold.fact_purchase_order_lines WHERE order_status IN ('Pending', 'Partially Received');")
        ).scalar()
        pass_pos = res_pos == 782
        print(f"Open POs:            {res_pos:,} (Expected: 782) -> {'PASS' if pass_pos else 'FAIL'}")
        all_passed = all_passed and pass_pos

        # Check 8: Operating Expenses
        res_opex = conn.execute(text("SELECT SUM(amount) FROM gold.fact_operating_expenses;")).scalar()
        val_opex = Decimal(str(res_opex or 0)).quantize(Decimal("0.01"))
        exp_opex = Decimal("39631974.10")
        pass_opex = val_opex == exp_opex
        print(f"Operating Expenses:  ${val_opex:,.2f} (Expected: ${exp_opex:,.2f}) -> {'PASS' if pass_opex else 'FAIL'}")
        all_passed = all_passed and pass_opex

        # Check 9: Goods Receipt Acceptance Rate
        res_accept_avg = conn.execute(text("SELECT ROUND((AVG(acceptance_rate) * 100)::numeric, 1) FROM gold.fact_goods_receipts;")).scalar()
        res_accept_agg = conn.execute(text("SELECT ROUND((SUM(accepted_qty)::numeric / SUM(received_qty) * 100), 1) FROM gold.fact_goods_receipts;")).scalar()
        pass_accept = float(res_accept_avg or 0) == 95.7 and float(res_accept_agg or 0) == 97.7
        print(f"Receipt Acceptance:  Avg: {res_accept_avg}%, Agg: {res_accept_agg}% (Expected: 95.7% / 97.7%) -> {'PASS' if pass_accept else 'FAIL'}")
        all_passed = all_passed and pass_accept

    print("========================================================")
    if all_passed:
        print(" ALL BUSINESS METRICS RECONCILED WITH 100% ACCURACY!")
    else:
        print("  SOME METRICS DID NOT MATCH.")
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replicate OpsPulse warehouse to Cloud PostgreSQL.")
    parser.add_argument("--target-url", required=True, help="Target PostgreSQL connection URL")
    args = parser.parse_args()

    success = migrate_warehouse(args.target_url)
    sys.exit(0 if success else 1)
