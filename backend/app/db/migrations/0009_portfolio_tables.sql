-- Asterion 0009 - portfolio tables

CREATE TABLE IF NOT EXISTS portfolios (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_positions (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    portfolio_id   BIGINT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker         TEXT NOT NULL,
    quantity       NUMERIC NOT NULL,
    average_cost   NUMERIC NOT NULL,
    current_price  NUMERIC,
    asset_type     TEXT,
    notes          TEXT,
    UNIQUE (portfolio_id, ticker)
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    portfolio_id   BIGINT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asof_date      DATE NOT NULL,
    total_value    NUMERIC NOT NULL,
    cash_balance   NUMERIC NOT NULL DEFAULT 0,
    UNIQUE (portfolio_id, asof_date)
);

CREATE TABLE IF NOT EXISTS portfolio_risk_metrics (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    portfolio_id   BIGINT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    metric_name    TEXT NOT NULL,
    value          NUMERIC NOT NULL,
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
