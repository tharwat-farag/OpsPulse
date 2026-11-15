import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))
from warehouse.db_connection import get_database_engine
from sqlalchemy import text

engine = get_database_engine()
with engine.connect() as conn:
    # Operating Expenses exact query
    r_opex_all = conn.execute(text('SELECT SUM(amount) FROM gold.fact_operating_expenses;')).scalar()
    r_opex_2025 = conn.execute(text('SELECT SUM(oe.amount) FROM gold.fact_operating_expenses oe JOIN gold.dim_date d ON oe.date_key = d.date_key WHERE d.year_number = 2025;')).scalar()
    print(f"OpEx (total):               {r_opex_all} (Decimal: {Decimal(str(r_opex_all)):.2f})")
    print(f"OpEx (2025 via dim_date):   {r_opex_2025} (Decimal: {Decimal(str(r_opex_2025)):.2f})")

    # Gross Sales, Discounts, Net Revenue, Gross Profit
    r_sales = conn.execute(text('SELECT SUM(gross_amount), SUM(discount_amount), SUM(net_revenue), SUM(gross_profit) FROM gold.fact_sales;')).fetchone()
    print(f"Gross Sales:                {r_sales[0]} ({Decimal(str(r_sales[0])):.2f})")
    print(f"Total Discounts:            {r_sales[1]} ({Decimal(str(r_sales[1])):.2f})")
    print(f"Net Revenue:                {r_sales[2]} ({Decimal(str(r_sales[2])):.2f})")
    print(f"Gross Profit:               {r_sales[3]} ({Decimal(str(r_sales[3])):.2f})")

    # Invoices
    r_inv_count = conn.execute(text('SELECT COUNT(DISTINCT invoice_id) FROM gold.fact_sales;')).scalar()
    print(f"Distinct Invoices:          {r_inv_count}")

    # Inventory
    r_inv_val = conn.execute(text('SELECT SUM(total_inventory_value) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);')).scalar()
    r_stockout = conn.execute(text('SELECT COUNT(CASE WHEN is_stockout THEN 1 END), COUNT(*) FROM gold.fact_inventory_snapshot WHERE date_key = (SELECT MAX(date_key) FROM gold.fact_inventory_snapshot);')).fetchone()
    print(f"Inventory Value:            {r_inv_val} ({Decimal(str(r_inv_val)):.2f})")
    print(f"Stockout Rate:              {r_stockout[0]}/{r_stockout[1]} = {r_stockout[0]/r_stockout[1]*100:.2f}%")

    # POs
    r_pos = conn.execute(text("SELECT COUNT(DISTINCT po_id) FROM gold.fact_purchase_order_lines WHERE order_status IN ('Pending', 'Partially Received');")).scalar()
    print(f"Open POs:                   {r_pos}")

    # Receipts
    r_rec = conn.execute(text('SELECT ROUND((AVG(acceptance_rate)*100)::numeric, 1), ROUND((SUM(accepted_qty)::numeric / SUM(received_qty)*100), 1) FROM gold.fact_goods_receipts;')).fetchone()
    print(f"Receipt Acceptance:         Avg per receipt: {r_rec[0]}%, Aggregate: {r_rec[1]}%")
