-- Asterion 0003 — market data.
-- prices_daily becomes a TimescaleDB hypertable when the extension is present;
-- otherwise it stays a plain table with a (ticker_id, date) PK + index. Either
-- way the schema and queries are identical.

CREATE TABLE IF NOT EXISTS prices_daily (
    ticker_id   BIGINT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    open        NUMERIC,
    high        NUMERIC,
    low         NUMERIC,
    close       NUMERIC,
    adj_close   NUMERIC,
    volume      BIGINT,
    vwap        NUMERIC,
    source      TEXT,                            -- provider name (provenance)
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker_id, date)
);
COMMENT ON TABLE prices_daily IS 'Asterion: daily OHLCV. Timescale hypertable if available.';
CREATE INDEX IF NOT EXISTS idx_prices_daily_ticker_date ON prices_daily(ticker_id, date DESC);

-- Conditionally convert to a hypertable (no-op without timescaledb).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('prices_daily', 'date',
                                  if_not_exists => TRUE, migrate_data => TRUE);
        RAISE NOTICE 'prices_daily converted to hypertable';
    ELSE
        RAISE NOTICE 'timescaledb absent — prices_daily remains a plain table';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS market_snapshots (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id       BIGINT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    asof            DATE NOT NULL,
    market_cap      NUMERIC,
    shares_outstanding NUMERIC,
    float_shares    NUMERIC,
    short_interest  NUMERIC,
    source          TEXT,
    retrieved_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ticker_id, asof)
);
COMMENT ON TABLE market_snapshots IS 'Asterion: point-in-time market cap / float / short interest.';

CREATE TABLE IF NOT EXISTS technical_indicators (
    ticker_id       BIGINT NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    name            TEXT NOT NULL,               -- e.g. rsi_14, ema_50
    value           NUMERIC,
    params          JSONB,
    formula_version TEXT,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker_id, date, name)
);
COMMENT ON TABLE technical_indicators IS 'Asterion: deterministically computed indicators (by quant engine, not from API).';
