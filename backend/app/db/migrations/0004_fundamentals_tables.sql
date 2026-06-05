-- Asterion 0004 — fundamentals.
-- financial_facts holds normalized XBRL facts from SEC companyfacts (one row per
-- concept/period/unit/filing). financial_ratios are PRE-COMPUTED by the quant
-- engine (M2) — never by an LLM. Both carry provenance.

CREATE TABLE IF NOT EXISTS financial_facts (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id      BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    taxonomy        TEXT NOT NULL,               -- us-gaap | dei | ifrs-full
    concept         TEXT NOT NULL,               -- XBRL tag, e.g. Revenues
    unit            TEXT NOT NULL,               -- USD, shares, USD/shares
    value           NUMERIC NOT NULL,
    period_start    DATE,
    period_end      DATE NOT NULL,
    fiscal_year     INT,
    fiscal_period   TEXT,                        -- FY, Q1..Q4
    form            TEXT,                        -- 10-K, 10-Q ...
    filed           DATE,
    frame           TEXT,                        -- SEC frame key if present
    accession_number TEXT,
    source_url      TEXT NOT NULL,
    retrieved_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash    TEXT NOT NULL,               -- hash of source payload (provenance)
    -- a single XBRL datapoint is uniquely identified by these. NULLS NOT DISTINCT
    -- (PG15+) so facts with a NULL fiscal_period / accession_number still dedup on
    -- re-ingest (otherwise NULL<>NULL and rows would duplicate every run).
    UNIQUE NULLS NOT DISTINCT
        (company_id, taxonomy, concept, unit, period_end, fiscal_period, accession_number)
);
COMMENT ON TABLE financial_facts IS 'Asterion: normalized XBRL facts from SEC companyfacts. Provenance on every row.';
CREATE INDEX IF NOT EXISTS idx_facts_company_concept ON financial_facts(company_id, concept, period_end DESC);

CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id      BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period_end      DATE NOT NULL,
    name            TEXT NOT NULL,               -- e.g. roic, fcf_yield
    value           NUMERIC,
    inputs          JSONB,                       -- raw inputs used (reproducibility)
    formula_version TEXT NOT NULL,
    confidence      NUMERIC,                     -- 0..1
    missing_penalty NUMERIC,                     -- 0..1 applied for imputed inputs
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, period_end, name)
);
COMMENT ON TABLE financial_ratios IS 'Asterion: deterministic ratios pre-computed by quant engine (M2). Reproducible from inputs.';

CREATE TABLE IF NOT EXISTS shares_outstanding_history (
    company_id   BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period_end   DATE NOT NULL,
    basic        NUMERIC,
    diluted      NUMERIC,
    source       TEXT,
    accession_number TEXT,
    PRIMARY KEY (company_id, period_end)
);
COMMENT ON TABLE shares_outstanding_history IS 'Asterion: share counts over time — dilution analysis.';

CREATE TABLE IF NOT EXISTS valuation_multiples (
    company_id        BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date              DATE NOT NULL,
    name              TEXT NOT NULL,             -- ev_ebitda, p_e, ev_sales ...
    value             NUMERIC,
    percentile_sector NUMERIC,                   -- cross-sectional percentile vs sector
    formula_version   TEXT,
    computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, date, name)
);
COMMENT ON TABLE valuation_multiples IS 'Asterion: relative multiples + sector percentile (computed, M2).';
