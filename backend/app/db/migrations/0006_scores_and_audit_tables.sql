-- Asterion 0006 — scoring (append-only, self-backtestable) + AI/RAG audit.
-- No score is written by an LLM. These tables exist now so the data spine and
-- audit trail are ready; scoring logic lands in M2 and the LLM layer in M4.

-- ---- Scoring (historical, append-only) ----
CREATE TABLE IF NOT EXISTS score_runs (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id            BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    asof                  DATE NOT NULL,
    regime                TEXT,
    formula_bundle_version TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE score_runs IS 'Asterion: one deterministic scoring pass. History retained to self-backtest predictions.';
CREATE INDEX IF NOT EXISTS idx_score_runs_company_asof ON score_runs(company_id, asof DESC);

CREATE TABLE IF NOT EXISTS factor_scores (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id           BIGINT NOT NULL REFERENCES score_runs(id) ON DELETE CASCADE,
    score_name       TEXT NOT NULL,              -- key from scoring.registry
    value            NUMERIC,                    -- 0..100
    raw_inputs       JSONB,
    confidence       NUMERIC,
    missing_penalty  NUMERIC,
    sector_percentile NUMERIC,
    UNIQUE (run_id, score_name)
);
COMMENT ON TABLE factor_scores IS 'Asterion: per-factor 0-100 scores with raw inputs (reproducible).';

CREATE TABLE IF NOT EXISTS final_scores (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id                  BIGINT NOT NULL REFERENCES score_runs(id) ON DELETE CASCADE,
    final_investment_score  NUMERIC,             -- regime-aware
    final_trading_score     NUMERIC,             -- WALLED OFF from investing
    regime                  TEXT,
    confidence              TEXT,                -- Low | Medium | High
    verdict                 TEXT,                -- Final Verdict Taxonomy
    UNIQUE (run_id)
);
COMMENT ON TABLE final_scores IS 'Asterion: investment vs trading kept in separate columns (walled garden).';

-- ---- AI / RAG audit ----
CREATE TABLE IF NOT EXISTS rag_queries (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_text    TEXT NOT NULL,
    qvec_model    TEXT,
    qvec_dim      INT,
    filters       JSONB,
    weight_version TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE rag_queries IS 'Asterion: logged retrieval queries (reproducibility).';

CREATE TABLE IF NOT EXISTS retrieval_results (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rag_query_id  BIGINT NOT NULL REFERENCES rag_queries(id) ON DELETE CASCADE,
    chunk_id      BIGINT REFERENCES document_chunks(id) ON DELETE SET NULL,
    vector_rank   INT,
    keyword_rank  INT,
    rrf           NUMERIC,
    final_score   NUMERIC
);
COMMENT ON TABLE retrieval_results IS 'Asterion: ranked retrieval output per query (audit).';

CREATE TABLE IF NOT EXISTS model_calls (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task          TEXT NOT NULL,
    model_name    TEXT NOT NULL,
    prompt_version TEXT,
    tokens_in     INT,
    tokens_out    INT,
    latency_ms    INT,
    temperature   NUMERIC,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE model_calls IS 'Asterion: every LLM call logged (even local). No call in M1.';

CREATE TABLE IF NOT EXISTS llm_outputs (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_call_id BIGINT NOT NULL REFERENCES model_calls(id) ON DELETE CASCADE,
    raw_output    TEXT,
    parsed        JSONB,
    schema_valid  BOOLEAN
);
COMMENT ON TABLE llm_outputs IS 'Asterion: raw + parsed LLM output for audit / hallucination checks.';
