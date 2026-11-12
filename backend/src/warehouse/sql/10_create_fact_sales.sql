
CREATE TABLE IF NOT EXISTS gold.fact_sales (
    sales_fact_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    sales_line_id VARCHAR(30) NOT NULL UNIQUE,
    invoice_id VARCHAR(30) NOT NULL,

    date_key INTEGER NOT NULL,
    product_key BIGINT NOT NULL,
    customer_key BIGINT NOT NULL,
    branch_key BIGINT NOT NULL,
    sales_channel_key SMALLINT NOT NULL,

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(14,2) NOT NULL,
    unit_cost NUMERIC(14,2) NOT NULL,

    gross_amount NUMERIC(16,2) NOT NULL,
    discount_amount NUMERIC(16,2) NOT NULL,
    net_revenue NUMERIC(16,2) NOT NULL,
    total_cost NUMERIC(16,2) NOT NULL,
    gross_profit NUMERIC(16,2) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_fact_sales_date
        FOREIGN KEY (date_key)
        REFERENCES gold.dim_date(date_key),

    CONSTRAINT fk_fact_sales_product
        FOREIGN KEY (product_key)
        REFERENCES gold.dim_product(product_key),

    CONSTRAINT fk_fact_sales_customer
        FOREIGN KEY (customer_key)
        REFERENCES gold.dim_customer(customer_key),

    CONSTRAINT fk_fact_sales_branch
        FOREIGN KEY (branch_key)
        REFERENCES gold.dim_branch(branch_key),

    CONSTRAINT fk_fact_sales_channel
        FOREIGN KEY (sales_channel_key)
        REFERENCES gold.dim_sales_channel(sales_channel_key),

    CONSTRAINT chk_fact_sales_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_fact_sales_amounts
        CHECK (
            unit_price >= 0
            AND unit_cost >= 0
            AND gross_amount >= 0
            AND discount_amount >= 0
            AND net_revenue >= 0
            AND total_cost >= 0
        )
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date
ON gold.fact_sales(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_product
ON gold.fact_sales(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer
ON gold.fact_sales(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_branch
ON gold.fact_sales(branch_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_channel
ON gold.fact_sales(sales_channel_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_invoice
ON gold.fact_sales(invoice_id);
