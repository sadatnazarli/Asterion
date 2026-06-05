-- Asterion 0001 — extensions.
-- pgcrypto: required (uuid / digest helpers).
-- vector:   used for embeddings in M3. Guarded so M1 runs without pgvector.
-- timescaledb: OHLCV hypertables. Guarded so M1 runs on a plain Postgres too.
-- Guards use a PL/pgSQL EXCEPTION block: a missing extension control file raises,
-- we catch it and continue (the rest of the schema does not depend on it in M1).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    RAISE NOTICE 'vector extension enabled';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'vector extension unavailable — skipping (embeddings arrive in M3)';
END $$;

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    RAISE NOTICE 'timescaledb extension enabled';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'timescaledb unavailable — OHLCV uses a plain table + index instead';
END $$;
