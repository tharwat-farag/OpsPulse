
CREATE TABLE IF NOT EXISTS gold.fact_purchase_order_lines (

    purchase_order_line_key BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    po_line_id VARCHAR(30) NOT NULL UNIQUE,
    po_id VARCHAR(30) NOT NULL,

    order_date_key INTEGER NOT NULL,
    expected_delivery_date_key INTEGER NOT NULL,

    product_key BIGINT NOT NULL,
    supplier_key BIGINT NOT NULL,

    ordered_qty INTEGER NOT NULL,
    unit_cost NUMERIC(14,2) NOT NULL,
    line_total NUMERIC(16,2) NOT NULL,

    order_status VARCHAR(40) NOT NULL,
    is_high_value_line BOOLEAN NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_po_line_order_date
        FOREIGN KEY (order_date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_po_line_expected_date
        FOREIGN KEY (expected_delivery_date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_po_line_product
        FOREIGN KEY (product_key)
        REFERENCES gold.dim_product(product_key),

    CONSTRAINT fk_po_line_supplier
        FOREIGN KEY (supplier_key)
        REFERENCES gold.dim_supplier(supplier_key),

    CONSTRAINT chk_po_line_quantity
        CHECK (ordered_qty > 0),

    CONSTRAINT chk_po_line_cost
        CHECK (unit_cost >= 0 AND line_total >= 0),

    CONSTRAINT chk_po_line_total
        CHECK (line_total = ordered_qty * unit_cost)
);

CREATE INDEX IF NOT EXISTS idx_fact_po_line_order_date
    ON gold.fact_purchase_order_lines(order_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_po_line_expected_date
    ON gold.fact_purchase_order_lines(expected_delivery_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_po_line_product
    ON gold.fact_purchase_order_lines(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_po_line_supplier
    ON gold.fact_purchase_order_lines(supplier_key);

CREATE INDEX IF NOT EXISTS idx_fact_po_line_po_id
    ON gold.fact_purchase_order_lines(po_id);
