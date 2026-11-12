
-- =====================================================
-- OpsPulse Gold Data Warehouse
-- Dimension: Date
-- =====================================================

CREATE TABLE IF NOT EXISTS gold.dim_date (

    date_key INTEGER PRIMARY KEY,

    full_date DATE NOT NULL UNIQUE,

    day_number SMALLINT NOT NULL,

    day_name VARCHAR(10) NOT NULL,

    month_number SMALLINT NOT NULL,

    month_name VARCHAR(15) NOT NULL,

    quarter_number SMALLINT NOT NULL,

    year_number SMALLINT NOT NULL,

    year_month VARCHAR(7) NOT NULL,

    is_month_start BOOLEAN NOT NULL,

    is_month_end BOOLEAN NOT NULL,

    CONSTRAINT chk_date_key
        CHECK (
            date_key =
            TO_CHAR(full_date, 'YYYYMMDD')::INTEGER
        ),

    CONSTRAINT chk_month_number
        CHECK (month_number BETWEEN 1 AND 12),

    CONSTRAINT chk_quarter_number
        CHECK (quarter_number BETWEEN 1 AND 4)

);


-- =====================================================
-- Populate Date Dimension
-- Coverage: 2025-01-01 to 2026-12-31
-- =====================================================

INSERT INTO gold.dim_date (

    date_key,
    full_date,
    day_number,
    day_name,
    month_number,
    month_name,
    quarter_number,
    year_number,
    year_month,
    is_month_start,
    is_month_end

)

SELECT

    TO_CHAR(d, 'YYYYMMDD')::INTEGER,

    d::DATE,

    EXTRACT(DAY FROM d)::SMALLINT,

    TO_CHAR(d, 'FMDay'),

    EXTRACT(MONTH FROM d)::SMALLINT,

    TO_CHAR(d, 'FMMonth'),

    EXTRACT(QUARTER FROM d)::SMALLINT,

    EXTRACT(YEAR FROM d)::SMALLINT,

    TO_CHAR(d, 'YYYY-MM'),

    (d = DATE_TRUNC('MONTH', d)::DATE),

    (
        d = (
            DATE_TRUNC('MONTH', d)
            + INTERVAL '1 MONTH'
            - INTERVAL '1 DAY'
        )::DATE
    )

FROM GENERATE_SERIES(

    DATE '2025-01-01',

    DATE '2026-12-31',

    INTERVAL '1 DAY'

) AS dates(d)

ON CONFLICT (date_key) DO NOTHING;


-- =====================================================
-- Validation
-- =====================================================

SELECT
    COUNT(*) AS total_dates,
    MIN(full_date) AS first_date,
    MAX(full_date) AS last_date
FROM gold.dim_date;
