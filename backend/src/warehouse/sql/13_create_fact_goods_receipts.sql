
CREATE TABLE IF NOT EXISTS gold.fact_goods_receipts (
    receipt_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    receipt_id VARCHAR(30) NOT NULL UNIQUE,
    po_id VARCHAR(30) NOT NULL,
    po_line_id VARCHAR(30) NOT NULL,

    received_date_key INTEGER NOT NULL,
    order_date_key INTEGER NOT NULL,
    expected_delivery_date_key INTEGER NOT NULL,

    product_key BIGINT NOT NULL,
    supplier_key BIGINT NOT NULL,

    received_qty INTEGER NOT NULL,
    accepted_qty INTEGER NOT NULL,
    rejected_qty INTEGER NOT NULL,

    acceptance_rate NUMERIC(10, 4) NOT NULL,

    days_from_order INTEGER NOT NULL,
    days_after_expected INTEGER NOT NULL,

    is_late_receipt BOOLEAN NOT NULL,
    is_fully_accepted BOOLEAN NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_receipt_received_date
        FOREIGN KEY (received_date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_receipt_order_date
        FOREIGN KEY (order_date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_receipt_expected_date
        FOREIGN KEY (expected_delivery_date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_receipt_product
        FOREIGN KEY (product_key)
        REFERENCES gold.dim_product(product_key),

    CONSTRAINT fk_receipt_supplier
        FOREIGN KEY (supplier_key)
        REFERENCES gold.dim_supplier(supplier_key),

    CONSTRAINT chk_receipt_quantities
        CHECK (
            received_qty > 0
            AND accepted_qty >= 0
            AND rejected_qty >= 0
            AND received_qty = accepted_qty + rejected_qty
        ),

    CONSTRAINT chk_receipt_acceptance_rate
        CHECK (acceptance_rate BETWEEN 0 AND 1),

    CONSTRAINT chk_receipt_days
        CHECK (days_from_order >= 0)
);

CREATE INDEX IF NOT EXISTS idx_receipts_received_date
    ON gold.fact_goods_receipts(received_date_key);

CREATE INDEX IF NOT EXISTS idx_receipts_order_date
    ON gold.fact_goods_receipts(order_date_key);

CREATE INDEX IF NOT EXISTS idx_receipts_product
    ON gold.fact_goods_receipts(product_key);

CREATE INDEX IF NOT EXISTS idx_receipts_supplier
    ON gold.fact_goods_receipts(supplier_key);

CREATE INDEX IF NOT EXISTS idx_receipts_po
    ON gold.fact_goods_receipts(po_id);

CREATE INDEX IF NOT EXISTS idx_receipts_po_line
    ON gold.fact_goods_receipts(po_line_id);
