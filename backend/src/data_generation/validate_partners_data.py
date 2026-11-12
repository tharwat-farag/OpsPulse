
import pandas as pd

from config import RAW_DATA_DIR


def validate_customers(customers):
    print("\nValidating Customers...")

    assert len(customers) == 1000, "Incorrect customer count"
    assert customers["customer_id"].is_unique, "Duplicate customer IDs"
    assert customers["customer_id"].notna().all(), "Null customer IDs"
    assert customers["customer_name"].notna().all(), "Null customer names"

    valid_types = {"Individual", "Business"}

    assert set(customers["customer_type"]).issubset(valid_types), (
        "Invalid customer type"
    )

    print("Customers validation passed!")


def validate_suppliers(suppliers):
    print("\nValidating Suppliers...")

    assert len(suppliers) == 10, "Incorrect supplier count"
    assert suppliers["supplier_id"].is_unique, "Duplicate supplier IDs"
    assert suppliers["supplier_id"].notna().all(), "Null supplier IDs"
    assert suppliers["contact_email"].notna().all(), "Null supplier emails"

    assert suppliers["rating"].between(1, 5).all(), (
        "Supplier rating must be between 1 and 5"
    )

    print("Suppliers validation passed!")


def validate_product_suppliers(
    relationships,
    products,
    suppliers,
):
    print("\nValidating Product-Supplier Relationships...")

    # Expected number of relationships
    assert len(relationships) == 150, (
        "Incorrect relationship count"
    )

    # No duplicate product-supplier pairs
    assert not relationships.duplicated(
        subset=["product_id", "supplier_id"]
    ).any(), "Duplicate product-supplier relationships"

    # Foreign key validation
    valid_products = set(products["product_id"])
    valid_suppliers = set(suppliers["supplier_id"])

    assert set(relationships["product_id"]).issubset(
        valid_products
    ), "Unknown product IDs found"

    assert set(relationships["supplier_id"]).issubset(
        valid_suppliers
    ), "Unknown supplier IDs found"

    # Every product must have at least one supplier
    supplier_counts = relationships.groupby(
        "product_id"
    ).size()

    assert set(supplier_counts.index) == valid_products, (
        "Some products have no suppliers"
    )

    # Exactly one preferred supplier per product
    preferred_counts = (
        relationships[
            relationships["is_preferred_supplier"]
        ]
        .groupby("product_id")
        .size()
    )

    assert len(preferred_counts) == len(valid_products), (
        "Some products have no preferred supplier"
    )

    assert (preferred_counts == 1).all(), (
        "A product has more than one preferred supplier"
    )

    # Business rule validation
    assert (relationships["supplier_price"] > 0).all(), (
        "Invalid supplier prices"
    )

    assert (relationships["lead_time_days"] > 0).all(), (
        "Invalid lead times"
    )

    assert (relationships["minimum_order_qty"] > 0).all(), (
        "Invalid minimum order quantities"
    )

    print("Product-Supplier validation passed!")


def main():
    customers = pd.read_csv(
        RAW_DATA_DIR / "customers.csv"
    )

    suppliers = pd.read_csv(
        RAW_DATA_DIR / "suppliers.csv"
    )

    relationships = pd.read_csv(
        RAW_DATA_DIR / "product_suppliers.csv"
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "products.csv"
    )

    validate_customers(customers)
    validate_suppliers(suppliers)

    validate_product_suppliers(
        relationships,
        products,
        suppliers,
    )

    print("\nALL PARTNERS DATA VALIDATIONS PASSED!")


if __name__ == "__main__":
    main()
