
CREATE TABLE IF NOT EXISTS gold.fact_operating_expenses (
    expense_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    expense_id VARCHAR(30) NOT NULL UNIQUE,

    date_key INTEGER NOT NULL,
    branch_key BIGINT NOT NULL,
    expense_category_key INTEGER NOT NULL,

    amount NUMERIC(14, 2) NOT NULL,

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_expense_date
        FOREIGN KEY (date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_expense_branch
        FOREIGN KEY (branch_key)
        REFERENCES gold.dim_branch(branch_key),

    CONSTRAINT fk_expense_category
        FOREIGN KEY (expense_category_key)
        REFERENCES gold.dim_expense_category(expense_category_key),

    CONSTRAINT chk_expense_amount
        CHECK (amount > 0)
);

CREATE INDEX IF NOT EXISTS idx_expenses_date
    ON gold.fact_operating_expenses(date_key);

CREATE INDEX IF NOT EXISTS idx_expenses_branch
    ON gold.fact_operating_expenses(branch_key);

CREATE INDEX IF NOT EXISTS idx_expenses_category
    ON gold.fact_operating_expenses(expense_category_key);
