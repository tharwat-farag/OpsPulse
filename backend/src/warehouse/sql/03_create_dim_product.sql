
CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    product_id VARCHAR(20) NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    brand VARCHAR(100) NOT NULL,

    standard_cost NUMERIC(14, 2) NOT NULL,
    current_selling_price NUMERIC(14, 2) NOT NULL,
    reorder_level INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_product_valid_period
        CHECK (valid_from < valid_to),

    CONSTRAINT chk_product_cost
        CHECK (standard_cost >= 0),

    CONSTRAINT chk_product_selling_price
        CHECK (current_selling_price >= 0),

    CONSTRAINT chk_product_reorder_level
        CHECK (reorder_level >= 0)
);

-- One current version per source product
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_dim_product_current
ON gold.dim_product (product_id)
WHERE is_current = TRUE;

-- Support historical version lookups
CREATE INDEX IF NOT EXISTS
    idx_dim_product_history
ON gold.dim_product (product_id, valid_from, valid_to);
