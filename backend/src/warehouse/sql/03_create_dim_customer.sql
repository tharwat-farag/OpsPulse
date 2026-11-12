
CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id VARCHAR(20) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_type VARCHAR(30) NOT NULL,
    city VARCHAR(100) NOT NULL,
    registration_date DATE NOT NULL,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_customer_valid_period
        CHECK (valid_from < valid_to),

    CONSTRAINT chk_customer_type
        CHECK (customer_type IN ('Business', 'Individual'))
);

-- Only one current version per customer
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_dim_customer_current
ON gold.dim_customer (customer_id)
WHERE is_current = TRUE;

-- Support historical lookups
CREATE INDEX IF NOT EXISTS
    idx_dim_customer_history
ON gold.dim_customer (customer_id, valid_from, valid_to);
