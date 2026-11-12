
import random
import pandas as pd

from datetime import timedelta

from config import (
    RANDOM_SEED,
    START_DATE,
    END_DATE,
    RAW_DATA_DIR,
)

random.seed(RANDOM_SEED)


# --------------------------------------------------
# 1. Load Reference Data
# --------------------------------------------------

def load_reference_data():

    suppliers = pd.read_csv(
        RAW_DATA_DIR / "suppliers.csv"
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    product_suppliers = pd.read_csv(
        RAW_DATA_DIR / "product_suppliers.csv"
    )

    return suppliers, products, product_suppliers


# --------------------------------------------------
# 2. Generate Purchase Orders
# --------------------------------------------------

def generate_procurement(
    suppliers,
    products,
    product_suppliers,
):

    purchase_orders = []
    purchase_order_lines = []
    goods_receipts = []

    # Map each supplier to the products they can supply.
    supplier_products = {}

    for supplier_id, group in product_suppliers.groupby(
        "supplier_id"
    ):
        supplier_products[supplier_id] = (
            group.to_dict("records")
        )

    # Only use suppliers that have at least 3 products.
    eligible_suppliers = [
        supplier_id
        for supplier_id, items in supplier_products.items()
        if len(items) >= 3
    ]

    if not eligible_suppliers:
        raise ValueError(
            "No supplier has at least 3 available products."
        )

    # Product lookup for standard product information.
    product_lookup = (
        products.set_index("product_id")
        .to_dict(orient="index")
    )

    po_line_number = 1
    receipt_number = 1

    total_days = (
        (END_DATE - START_DATE).days - 14
    )

    # Generate 1,000 Purchase Orders.
    for po_number in range(1, 1001):

        po_id = f"PO{po_number:04d}"

        supplier_id = random.choice(
            eligible_suppliers
        )

        available_products = supplier_products[
            supplier_id
        ]

        # Every PO contains exactly 3 different products.
        selected_items = random.sample(
            available_products,
            3,
        )

        # Generate order and expected delivery dates.
        order_date = START_DATE + timedelta(
            days=random.randint(0, total_days)
        )

        expected_delivery_date = (
            order_date
            + timedelta(days=random.randint(3, 14))
        )

        # Determine the PO scenario.
        scenario = random.choices(
            [
                "Fully Received",
                "Partially Received",
                "Pending",
                "Cancelled",
            ],
            weights=[15, 75, 5, 5],
            k=1,
        )[0]

        po_lines_for_order = []

        # Generate 3 PO Lines.
        for item in selected_items:

            product_id = item["product_id"]

            ordered_qty = random.randint(20, 100)

            supplier_price = item["supplier_price"]

            unit_cost = round(
                supplier_price * random.uniform(
                    0.98,
                    1.02,
                ),
                2,
            )

            po_line_id = (
                f"POL{po_line_number:05d}"
            )

            line = {
                "po_line_id": po_line_id,
                "po_id": po_id,
                "product_id": product_id,
                "ordered_qty": ordered_qty,
                "unit_cost": unit_cost,
            }

            purchase_order_lines.append(line)

            po_lines_for_order.append(line)

            po_line_number += 1

        # ------------------------------------------
        # Generate Goods Receipts
        # ------------------------------------------

        if scenario == "Fully Received":

            # Every line is fully delivered.
            for line in po_lines_for_order:

                ordered_qty = line["ordered_qty"]

                # Sometimes the supplier delivers in two batches.
                if random.random() < 0.5:

                    first_qty = random.randint(
                        1,
                        ordered_qty - 1,
                    )

                    receipt_quantities = [
                        first_qty,
                        ordered_qty - first_qty,
                    ]

                else:

                    receipt_quantities = [
                        ordered_qty
                    ]

                for batch_number, received_qty in enumerate(
                    receipt_quantities
                ):

                    received_date = (
                        expected_delivery_date
                        + timedelta(
                            days=random.randint(-2, 5)
                            + batch_number
                        )
                    )

                    rejected_qty = random.randint(
                        0,
                        min(
                            received_qty,
                            max(1, int(received_qty * 0.05)),
                        ),
                    )

                    accepted_qty = (
                        received_qty - rejected_qty
                    )

                    goods_receipts.append({
                        "receipt_id": (
                            f"GR{receipt_number:05d}"
                        ),
                        "po_line_id": line["po_line_id"],
                        "received_date": received_date,
                        "received_qty": received_qty,
                        "accepted_qty": accepted_qty,
                        "rejected_qty": rejected_qty,
                    })

                    receipt_number += 1

        elif scenario == "Partially Received":

            # Only one of the three lines is partially delivered.
            selected_line = random.choice(
                po_lines_for_order
            )

            ordered_qty = selected_line["ordered_qty"]

            received_qty = random.randint(
                1,
                ordered_qty - 1,
            )

            rejected_qty = random.randint(
                0,
                min(
                    received_qty,
                    max(1, int(received_qty * 0.05)),
                ),
            )

            accepted_qty = (
                received_qty - rejected_qty
            )

            received_date = (
                expected_delivery_date
                + timedelta(days=random.randint(-2, 5))
            )

            goods_receipts.append({
                "receipt_id": f"GR{receipt_number:05d}",
                "po_line_id": selected_line["po_line_id"],
                "received_date": received_date,
                "received_qty": received_qty,
                "accepted_qty": accepted_qty,
                "rejected_qty": rejected_qty,
            })

            receipt_number += 1

        # Pending and Cancelled orders have no receipts.

        purchase_orders.append({
            "po_id": po_id,
            "supplier_id": supplier_id,
            "order_date": order_date,
            "expected_delivery_date": expected_delivery_date,
            "status": scenario,
        })

    return (
        pd.DataFrame(purchase_orders),
        pd.DataFrame(purchase_order_lines),
        pd.DataFrame(goods_receipts),
    )


# --------------------------------------------------
# 3. Save Generated Data
# --------------------------------------------------

def save_dataframe(df, filename):

    output_path = RAW_DATA_DIR / filename

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Saved: {output_path}")
    print(f"Records: {len(df)}")


# --------------------------------------------------
# 4. Main
# --------------------------------------------------

def main():

    print("Starting Procurement Data Generation...")

    suppliers, products, product_suppliers = (
        load_reference_data()
    )

    (
        purchase_orders,
        purchase_order_lines,
        goods_receipts,
    ) = generate_procurement(
        suppliers,
        products,
        product_suppliers,
    )

    save_dataframe(
        purchase_orders,
        "purchase_orders.csv",
    )

    save_dataframe(
        purchase_order_lines,
        "purchase_order_lines.csv",
    )

    save_dataframe(
        goods_receipts,
        "goods_receipts.csv",
    )

    print("\n========== PROCUREMENT SUMMARY ==========")

    print(
        f"Purchase Orders: {len(purchase_orders)}"
    )

    print(
        f"Purchase Order Lines: {len(purchase_order_lines)}"
    )

    print(
        f"Goods Receipts: {len(goods_receipts)}"
    )

    print("\nPurchase Order Status Distribution:")

    print(
        purchase_orders["status"].value_counts()
    )

    print("\nGoods Receipts Preview:")

    print(goods_receipts.head())

    print("\nProcurement Data Generation Completed!")


if __name__ == "__main__":
    main()
