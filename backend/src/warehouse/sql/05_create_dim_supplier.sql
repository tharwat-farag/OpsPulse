
CREATE TABLE IF NOT EXISTS gold.dim_supplier (
    supplier_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    supplier_id VARCHAR(20) NOT NULL,
    supplier_name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    rating NUMERIC(3,2) NOT NULL,
    is_active BOOLEAN NOT NULL,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_dim_supplier_valid_period
        CHECK (valid_from < valid_to),

    CONSTRAINT chk_dim_supplier_rating
        CHECK (rating >= 0 AND rating <= 5)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_supplier_current
ON gold.dim_supplier (supplier_id)
WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_dim_supplier_history
ON gold.dim_supplier (supplier_id, valid_from, valid_to);
