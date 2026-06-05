-- Asterion 0002 — core reference + entity tables.
-- Survivorship principle: companies.is_active retains delisted entities.

CREATE TABLE IF NOT EXISTS exchanges (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,           -- e.g. XNAS, XNYS
    name        TEXT,
    country     TEXT,
    mic         TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE exchanges IS 'Asterion: trading venues.';

CREATE TABLE IF NOT EXISTS sectors (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gics_code   TEXT UNIQUE,
    name        TEXT NOT NULL UNIQUE
);
COMMENT ON TABLE sectors IS 'Asterion: GICS sectors — drive sector-relative score normalization.';

CREATE TABLE IF NOT EXISTS industries (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gics_code   TEXT UNIQUE,
    name        TEXT NOT NULL,
    sector_id   BIGINT REFERENCES sectors(id) ON DELETE SET NULL,
    UNIQUE (name, sector_id)
);
COMMENT ON TABLE industries IS 'Asterion: GICS industries within sectors.';

CREATE TABLE IF NOT EXISTS companies (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cik           TEXT NOT NULL UNIQUE,          -- zero-padded 10-digit SEC CIK
    name          TEXT NOT NULL,
    sector_id     BIGINT REFERENCES sectors(id) ON DELETE SET NULL,
    industry_id   BIGINT REFERENCES industries(id) ON DELETE SET NULL,
    sic           TEXT,                          -- SEC SIC code (raw)
    sic_description TEXT,
    country       TEXT,
    fiscal_year_end TEXT,                        -- MMDD from SEC submissions
    market_cap    NUMERIC,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE, -- survivorship: false = delisted, row retained
    delisted_at   DATE,
    first_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE companies IS 'Asterion: issuer master. is_active retains delisted firms (survivorship-safe).';
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);

CREATE TABLE IF NOT EXISTS tickers (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id   BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL,
    exchange_id  BIGINT REFERENCES exchanges(id) ON DELETE SET NULL,
    is_primary   BOOLEAN NOT NULL DEFAULT TRUE,
    active_from  DATE,
    active_to    DATE,                           -- null = currently active; handles symbol changes / dual listings
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (symbol, company_id)
);
COMMENT ON TABLE tickers IS 'Asterion: symbol mapping — supports symbol changes and dual listings.';
CREATE INDEX IF NOT EXISTS idx_tickers_symbol ON tickers(symbol);
