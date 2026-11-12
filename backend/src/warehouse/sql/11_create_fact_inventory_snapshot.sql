
CREATE TABLE IF NOT EXISTS gold.fact_inventory_snapshot (

    inventory_snapshot_key BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    inventory_snapshot_id VARCHAR(30) NOT NULL UNIQUE,

    date_key INTEGER NOT NULL,
    product_key BIGINT NOT NULL,
    warehouse_key BIGINT NOT NULL,

    quantity_on_hand INTEGER NOT NULL,
    quantity_reserved INTEGER NOT NULL,
    available_quantity INTEGER NOT NULL,

    standard_cost NUMERIC(14,2) NOT NULL,

    total_inventory_value NUMERIC(16,2) NOT NULL,
    available_inventory_value NUMERIC(16,2) NOT NULL,
    reserved_inventory_value NUMERIC(16,2) NOT NULL,

    capacity_units INTEGER NOT NULL,
    warehouse_total_on_hand INTEGER NOT NULL,
    capacity_utilization_pct NUMERIC(8,4) NOT NULL,

    is_stockout BOOLEAN NOT NULL,
    is_fully_reserved BOOLEAN NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_date
        FOREIGN KEY (date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_key)
        REFERENCES gold.dim_product(product_key),

    CONSTRAINT fk_inventory_warehouse
        FOREIGN KEY (warehouse_key)
        REFERENCES gold.dim_warehouse(warehouse_key),

    CONSTRAINT uq_inventory_snapshot_grain
        UNIQUE (date_key, product_key, warehouse_key),

    CONSTRAINT chk_inventory_quantities
        CHECK (
            quantity_on_hand >= 0
            AND quantity_reserved >= 0
            AND available_quantity >= 0
            AND quantity_reserved <= quantity_on_hand
        ),

    CONSTRAINT chk_inventory_values
        CHECK (
            standard_cost >= 0
            AND total_inventory_value >= 0
            AND available_inventory_value >= 0
            AND reserved_inventory_value >= 0
        ),

    CONSTRAINT chk_inventory_capacity
        CHECK (
            capacity_units > 0
            AND warehouse_total_on_hand >= 0
            AND capacity_utilization_pct >= 0
        )
);

-- Indexes for analytical queries

CREATE INDEX IF NOT EXISTS idx_fact_inventory_date
    ON gold.fact_inventory_snapshot(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_inventory_product
    ON gold.fact_inventory_snapshot(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_inventory_warehouse
    ON gold.fact_inventory_snapshot(warehouse_key);
