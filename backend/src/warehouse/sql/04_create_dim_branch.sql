
CREATE TABLE IF NOT EXISTS gold.dim_branch (
    branch_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    branch_id VARCHAR(20) NOT NULL,
    branch_name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    manager_name VARCHAR(150) NOT NULL,
    opening_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL,

    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_dim_branch_valid_period
        CHECK (valid_from < valid_to)
);

-- One current version per branch
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_branch_current
ON gold.dim_branch (branch_id)
WHERE is_current = TRUE;

-- Support historical version lookups
CREATE INDEX IF NOT EXISTS idx_dim_branch_history
ON gold.dim_branch (branch_id, valid_from, valid_to);
