
-- OpsPulse | Branch-Warehouse Mapping Bridge
-- Synthetic operational mapping for Nexa Distribution Group

CREATE TABLE IF NOT EXISTS gold.bridge_branch_warehouse (
    branch_warehouse_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    branch_key BIGINT NOT NULL,
    warehouse_key BIGINT NOT NULL,

    is_primary BOOLEAN NOT NULL DEFAULT TRUE,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',

    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_branch_warehouse_branch
        FOREIGN KEY (branch_key)
        REFERENCES gold.dim_branch (branch_key),

    CONSTRAINT fk_branch_warehouse_warehouse
        FOREIGN KEY (warehouse_key)
        REFERENCES gold.dim_warehouse (warehouse_key),

    CONSTRAINT chk_branch_warehouse_valid_period
        CHECK (valid_from < valid_to)
);

-- Prevent duplicate current mappings
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_branch_warehouse_current_mapping
ON gold.bridge_branch_warehouse (
    branch_key,
    warehouse_key
)
WHERE is_current = TRUE;

-- Each branch can have only one current primary warehouse
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_branch_current_primary_warehouse
ON gold.bridge_branch_warehouse (branch_key)
WHERE is_current = TRUE
  AND is_primary = TRUE;

CREATE INDEX IF NOT EXISTS
    idx_branch_warehouse_warehouse
ON gold.bridge_branch_warehouse (warehouse_key);
