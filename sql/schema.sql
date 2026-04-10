CREATE TABLE IF NOT EXISTS raw_import_batches (
    batch_id TEXT PRIMARY KEY,
    source_file_name TEXT NOT NULL,
    source_file_path TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    file_date DATE,
    imported_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS raw_excel_rows (
    batch_id TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    col_01 TEXT,
    col_02 TEXT,
    col_03 TEXT,
    col_04 TEXT,
    col_05 TEXT,
    col_06 TEXT,
    col_07 TEXT,
    col_08 TEXT,
    col_09 TEXT,
    col_10 TEXT,
    col_11 TEXT,
    col_12 TEXT,
    col_13 TEXT,
    col_14 TEXT,
    col_15 TEXT,
    col_16 TEXT,
    col_17 TEXT,
    col_18 TEXT,
    col_19 TEXT,
    col_20 TEXT,
    raw_json TEXT,
    loaded_at TIMESTAMP NOT NULL,
    PRIMARY KEY (batch_id, sheet_name, row_number)
);

CREATE TABLE IF NOT EXISTS stg_bond_position (
    batch_id TEXT NOT NULL,
    isin TEXT NOT NULL,
    company_code TEXT,
    bond_type TEXT,
    counterparty TEXT,
    product_name TEXT,
    issuer_name TEXT,
    industry TEXT,
    currency TEXT,
    rating_text TEXT,
    rating_bucket TEXT,
    coupon_rate NUMERIC,
    coupon_frequency NUMERIC,
    trade_date DATE,
    duration_years NUMERIC,
    maturity_date DATE,
    purchase_price NUMERIC,
    ytm NUMERIC,
    face_amount NUMERIC,
    principal_amount NUMERIC,
    accrued_interest NUMERIC,
    settlement_amount NUMERIC,
    settlement_date DATE,
    coupon_count NUMERIC,
    receivable_interest NUMERIC,
    cash_total NUMERIC,
    yield_band TEXT,
    duration_band TEXT,
    weighted_cost NUMERIC,
    total_investment NUMERIC,
    avg_duration_years NUMERIC,
    avg_yield NUMERIC,
    total_profit NUMERIC,
    total_profit_rate NUMERIC
);

CREATE TABLE IF NOT EXISTS stg_bond_cashflow (
    batch_id TEXT NOT NULL,
    isin TEXT,
    company_code TEXT,
    bond_type TEXT,
    counterparty TEXT,
    cashflow_date DATE,
    coupon_amount NUMERIC,
    total_payback NUMERIC,
    cashflow_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stg_bond_limit (
    batch_id TEXT NOT NULL,
    rating_bucket TEXT,
    moodys_rating TEXT,
    sp_rating TEXT,
    fitch_rating TEXT,
    investment_limit_usd NUMERIC,
    note TEXT
);

CREATE TABLE IF NOT EXISTS mart_bond_dashboard_position (
    batch_id TEXT NOT NULL,
    isin TEXT,
    company_code TEXT,
    issuer_name TEXT,
    counterparty TEXT,
    currency TEXT,
    rating_bucket TEXT,
    bond_type TEXT,
    face_amount NUMERIC,
    settlement_amount NUMERIC,
    ytm NUMERIC,
    duration_years NUMERIC,
    maturity_date DATE,
    maturity_year INTEGER,
    portfolio_weight NUMERIC
);

CREATE TABLE IF NOT EXISTS mart_bond_dashboard_cashflow (
    batch_id TEXT NOT NULL,
    cashflow_year INTEGER,
    cashflow_month INTEGER,
    cashflow_type TEXT,
    total_payback NUMERIC
);

CREATE TABLE IF NOT EXISTS mart_bond_dashboard_limit_usage (
    batch_id TEXT NOT NULL,
    rating_bucket TEXT,
    current_exposure NUMERIC,
    investment_limit_usd NUMERIC,
    usage_ratio NUMERIC,
    note TEXT
);

CREATE TABLE IF NOT EXISTS mart_ai_alerts (
    batch_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    entity_name TEXT,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL
);
