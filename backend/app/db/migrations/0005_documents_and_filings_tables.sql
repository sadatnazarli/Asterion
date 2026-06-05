-- Asterion 0005 — documents, filings, chunks, citations.
-- Every ingested document carries provenance. document_chunks include a generated
-- tsvector for BM25-style keyword search (GIN). The pgvector embedding column is
-- added in M3 (kept out of M1 so this runs without the vector extension).

CREATE TABLE IF NOT EXISTS raw_documents (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id    BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,                 -- sec_submissions, sec_companyfacts, 10-K, 10-Q, transcript, user_upload ...
    source_name   TEXT NOT NULL,                 -- e.g. SEC EDGAR
    source_url    TEXT,
    accession_number TEXT,
    license_note  TEXT,
    storage_path  TEXT,                          -- path under data/raw_documents if persisted
    content_hash  TEXT NOT NULL UNIQUE,          -- sha256 of raw payload (dedup + provenance)
    retrieved_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta          JSONB
);
COMMENT ON TABLE raw_documents IS 'Asterion: provenance anchor for every ingested document/payload.';
CREATE INDEX IF NOT EXISTS idx_raw_docs_company_type ON raw_documents(company_id, document_type);

CREATE TABLE IF NOT EXISTS filings (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id       BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    accession_number TEXT NOT NULL UNIQUE,
    form_type        TEXT NOT NULL,              -- 10-K, 10-Q, 8-K, 4, 13F ...
    filing_date      DATE,
    period_of_report DATE,
    primary_doc      TEXT,                        -- primary document filename
    primary_doc_url  TEXT,
    raw_document_id  BIGINT REFERENCES raw_documents(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE filings IS 'Asterion: SEC filing index (from submissions API).';
CREATE INDEX IF NOT EXISTS idx_filings_company_form ON filings(company_id, form_type, filing_date DESC);

CREATE TABLE IF NOT EXISTS document_chunks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_document_id BIGINT REFERENCES raw_documents(id) ON DELETE CASCADE,
    company_id      BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    ticker          TEXT,
    document_type   TEXT,
    filing_type     TEXT,
    fiscal_period   TEXT,
    filing_date     DATE,
    section_name    TEXT,
    page_number     INT,
    accession_number TEXT,
    text            TEXT NOT NULL,
    text_hash       TEXT NOT NULL,
    tsv             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE document_chunks IS 'Asterion: section-aware chunks. tsv = keyword search; embeddings added in M3.';
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON document_chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_company ON document_chunks(company_id, document_type);

CREATE TABLE IF NOT EXISTS source_citations (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chunk_id         BIGINT REFERENCES document_chunks(id) ON DELETE CASCADE,
    ticker           TEXT,
    document_type    TEXT,
    filing_date      DATE,
    section          TEXT,
    accession_number TEXT,
    source_url       TEXT,
    char_span        INT4RANGE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE source_citations IS 'Asterion: citation attached to every LLM output and alert.';
