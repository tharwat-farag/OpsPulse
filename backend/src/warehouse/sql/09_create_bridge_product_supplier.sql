
CREATE TABLE IF NOT EXISTS gold.bridge_product_supplier (
    product_key BIGINT NOT NULL,
    supplier_key BIGINT NOT NULL,

    supplier_price NUMERIC(14,2) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    minimum_order_qty INTEGER NOT NULL,
    is_preferred_supplier BOOLEAN NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_bridge_product_supplier
        PRIMARY KEY (product_key, supplier_key),

    CONSTRAINT fk_bridge_product
        FOREIGN KEY (product_key)
        REFERENCES gold.dim_product (product_key),

    CONSTRAINT fk_bridge_supplier
        FOREIGN KEY (supplier_key)
        REFERENCES gold.dim_supplier (supplier_key),

    CONSTRAINT chk_bridge_supplier_price
        CHECK (supplier_price >= 0),

    CONSTRAINT chk_bridge_lead_time
        CHECK (lead_time_days >= 0),

    CONSTRAINT chk_bridge_minimum_order
        CHECK (minimum_order_qty > 0)
);

CREATE INDEX IF NOT EXISTS idx_bridge_supplier_product
ON gold.bridge_product_supplier (supplier_key, product_key);
