
import pandas as pd

from config import RAW_DATA_DIR


def load_data():

    purchase_orders = pd.read_csv(
        RAW_DATA_DIR / "purchase_orders.csv",
        parse_dates=["order_date", "expected_delivery_date"],
    )

    purchase_order_lines = pd.read_csv(
        RAW_DATA_DIR / "purchase_order_lines.csv"
    )

    goods_receipts = pd.read_csv(
        RAW_DATA_DIR / "goods_receipts.csv",
        parse_dates=["received_date"],
    )

    suppliers = pd.read_csv(
        RAW_DATA_DIR / "suppliers.csv"
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    product_suppliers = pd.read_csv(
        RAW_DATA_DIR / "product_suppliers.csv"
    )

    return (
        purchase_orders,
        purchase_order_lines,
        goods_receipts,
        suppliers,
        products,
        product_suppliers,
    )


def validate_basic_rules(po, lines, receipts):

    print("\nValidating Basic Rules...")

    assert len(po) == 1000, "Incorrect PO count"

    assert len(lines) == 3000, "Incorrect PO Lines count"

    assert po["po_id"].is_unique, "Duplicate PO IDs"

    assert lines["po_line_id"].is_unique, (
        "Duplicate PO Line IDs"
    )

    assert receipts["receipt_id"].is_unique, (
        "Duplicate Receipt IDs"
    )

    required_po_columns = [
        "supplier_id",
        "order_date",
        "expected_delivery_date",
        "status",
    ]

    assert po[required_po_columns].notna().all().all(), (
        "Null values found in Purchase Orders"
    )

    required_line_columns = [
        "po_id",
        "product_id",
        "ordered_qty",
        "unit_cost",
    ]

    assert lines[required_line_columns].notna().all().all(), (
        "Null values found in Purchase Order Lines"
    )

    required_receipt_columns = [
        "po_line_id",
        "received_date",
        "received_qty",
        "accepted_qty",
        "rejected_qty",
    ]

    assert receipts[required_receipt_columns].notna().all().all(), (
        "Null values found in Goods Receipts"
    )

    assert (lines["ordered_qty"] > 0).all(), (
        "Invalid ordered quantities"
    )

    assert (lines["unit_cost"] > 0).all(), (
        "Invalid purchase costs"
    )

    valid_statuses = {
        "Pending",
        "Partially Received",
        "Fully Received",
        "Cancelled",
    }

    assert set(po["status"]).issubset(valid_statuses), (
        "Invalid Purchase Order status"
    )

    print("Basic Rules Passed!")


def validate_foreign_keys(
    po,
    lines,
    receipts,
    suppliers,
    products,
    product_suppliers,
):

    print("\nValidating Foreign Keys...")

    assert set(po["supplier_id"]).issubset(
        set(suppliers["supplier_id"])
    ), "Unknown supplier IDs in Purchase Orders"

    assert set(lines["po_id"]).issubset(
        set(po["po_id"])
    ), "Unknown PO IDs in Purchase Order Lines"

    assert set(lines["product_id"]).issubset(
        set(products["product_id"])
    ), "Unknown product IDs in Purchase Order Lines"

    assert set(receipts["po_line_id"]).issubset(
        set(lines["po_line_id"])
    ), "Unknown PO Line IDs in Goods Receipts"

    # Verify that each supplier can supply the ordered product.
    po_supplier_lines = lines.merge(
        po[["po_id", "supplier_id"]],
        on="po_id",
        how="left",
    )

    valid_pairs = set(
        zip(
            product_suppliers["product_id"],
            product_suppliers["supplier_id"],
        )
    )

    actual_pairs = set(
        zip(
            po_supplier_lines["product_id"],
            po_supplier_lines["supplier_id"],
        )
    )

    assert actual_pairs.issubset(valid_pairs), (
        "A supplier was assigned a product it cannot supply"
    )

    print("Foreign Key Validation Passed!")


def validate_receipt_quantities(lines, receipts):

    print("\nValidating Receipt Quantities...")

    # Accepted + Rejected must equal Received.
    assert (
        receipts["accepted_qty"]
        + receipts["rejected_qty"]
        == receipts["received_qty"]
    ).all(), "Receipt quantity calculation mismatch"

    assert (receipts["received_qty"] > 0).all(), (
        "Invalid received quantity"
    )

    assert (receipts["accepted_qty"] >= 0).all(), (
        "Negative accepted quantity"
    )

    assert (receipts["rejected_qty"] >= 0).all(), (
        "Negative rejected quantity"
    )

    # Calculate total received quantity per PO Line.
    received_totals = (
        receipts.groupby("po_line_id")["received_qty"]
        .sum()
    )

    ordered_totals = lines.set_index(
        "po_line_id"
    )["ordered_qty"]

    # No PO Line can receive more than ordered.
    for po_line_id, received_qty in received_totals.items():

        ordered_qty = ordered_totals.loc[po_line_id]

        assert received_qty <= ordered_qty, (
            f"Received quantity exceeds ordered quantity: {po_line_id}"
        )

    print("Receipt Quantity Validation Passed!")


def validate_purchase_order_status(po, lines, receipts):

    print("\nValidating Purchase Order Status...")

    # Attach PO IDs to receipt records.
    receipt_details = receipts.merge(
        lines[["po_line_id", "po_id"]],
        on="po_line_id",
        how="left",
    )

    received_per_po = (
        receipt_details.groupby("po_id")["received_qty"]
        .sum()
    )

    ordered_per_po = (
        lines.groupby("po_id")["ordered_qty"]
        .sum()
    )

    po_check = po.set_index("po_id").copy()

    po_check["ordered_qty"] = ordered_per_po

    po_check["received_qty"] = (
        received_per_po.reindex(
            po_check.index,
            fill_value=0,
        )
    )

    for po_id, row in po_check.iterrows():

        ordered = row["ordered_qty"]
        received = row["received_qty"]
        status = row["status"]

        if status == "Fully Received":
            assert received == ordered, (
                f"{po_id} is Fully Received but quantities do not match"
            )

        elif status == "Partially Received":
            assert 0 < received < ordered, (
                f"{po_id} has an invalid Partially Received status"
            )

        elif status in {"Pending", "Cancelled"}:
            assert received == 0, (
                f"{po_id} has receipts despite status {status}"
            )

    print("Purchase Order Status Validation Passed!")


def validate_receipt_dates(po, lines, receipts):

    print("\nValidating Receipt Dates...")

    receipt_details = receipts.merge(
        lines[["po_line_id", "po_id"]],
        on="po_line_id",
        how="left",
    )

    receipt_details = receipt_details.merge(
        po[["po_id", "order_date", "expected_delivery_date"]],
        on="po_id",
        how="left",
    )

    assert (
        receipt_details["received_date"]
        >= receipt_details["order_date"]
    ).all(), "Receipt date is before order date"

    assert (
        po["expected_delivery_date"] >= po["order_date"]
    ).all(), "Expected delivery date is before order date"

    print("Receipt Date Validation Passed!")


def display_procurement_summary(po, lines, receipts):

    print("\n========== PROCUREMENT QUALITY SUMMARY ==========")

    print(f"Purchase Orders: {len(po)}")
    print(f"Purchase Order Lines: {len(lines)}")
    print(f"Goods Receipts: {len(receipts)}")

    print("\nPO Status Distribution:")
    print(po["status"].value_counts())

    total_ordered = lines["ordered_qty"].sum()

    total_received = receipts["received_qty"].sum()

    total_accepted = receipts["accepted_qty"].sum()

    total_rejected = receipts["rejected_qty"].sum()

    print("\nQuantity Summary:")

    print(f"Total Ordered: {total_ordered:,}")
    print(f"Total Received: {total_received:,}")
    print(f"Total Accepted: {total_accepted:,}")
    print(f"Total Rejected: {total_rejected:,}")

    rejection_rate = (
        total_rejected / total_received * 100
        if total_received > 0
        else 0
    )

    print(f"Rejection Rate: {rejection_rate:.2f}%")

    print("\n==================================================")


def main():

    print("Starting Procurement Data Validation...")

    (
        po,
        lines,
        receipts,
        suppliers,
        products,
        product_suppliers,
    ) = load_data()

    validate_basic_rules(po, lines, receipts)

    validate_foreign_keys(
        po,
        lines,
        receipts,
        suppliers,
        products,
        product_suppliers,
    )

    validate_receipt_quantities(lines, receipts)

    validate_purchase_order_status(
        po,
        lines,
        receipts,
    )

    validate_receipt_dates(
        po,
        lines,
        receipts,
    )

    display_procurement_summary(
        po,
        lines,
        receipts,
    )

    print("\nALL PROCUREMENT VALIDATIONS PASSED!")


if __name__ == "__main__":
    main()
