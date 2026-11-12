
CREATE TABLE IF NOT EXISTS gold.dim_warehouse (
    warehouse_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    warehouse_id VARCHAR(20) NOT NULL,
    warehouse_name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    capacity_units INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_dim_warehouse_valid_period
        CHECK (valid_from < valid_to),

    CONSTRAINT chk_dim_warehouse_capacity
        CHECK (capacity_units > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_warehouse_current
ON gold.dim_warehouse (warehouse_id)
WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_dim_warehouse_history
ON gold.dim_warehouse (warehouse_id, valid_from, valid_to);
