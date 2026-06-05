# 09 — M1: Data Spine (SEC ingestion + PLTR)

Trace: `MASTER_PLAN.md` §12 (M1). Goal of M1: a real, reproducible data spine —
PostgreSQL schema + SEC EDGAR ingestion + one ticker (PLTR) ingested end-to-end.
**No LLM, no scores, no UI, no fabricated numbers.** Only structured SEC data with
provenance.

---

## 1. What was implemented

### Migrations (`backend/app/db/migrations/`)
Six ordered, idempotent raw-SQL files applied by `scripts/migrate.py` (tracks
applied files in `schema_migrations`):

| File | Tables |
|------|--------|
| `0001_extensions.sql` | `pgcrypto` (required); `vector` + `timescaledb` **guarded** (skip cleanly if absent) |
| `0002_core_tables.sql` | exchanges, sectors, industries, **companies** (`is_active` survivorship), tickers |
| `0003_market_data_tables.sql` | prices_daily (Timescale hypertable *if available*, else plain), market_snapshots, technical_indicators |
| `0004_fundamentals_tables.sql` | **financial_facts** (XBRL), financial_ratios, shares_outstanding_history, valuation_multiples |
| `0005_documents_and_filings_tables.sql` | raw_documents, filings, document_chunks (`tsv` GIN), source_citations |
| `0006_scores_and_audit_tables.sql` | score_runs, factor_scores, final_scores, rag_queries, retrieval_results, model_calls, llm_outputs |

24 tables total (incl. `schema_migrations`). Extensions degrade gracefully: on a
plain Postgres (no pgvector/timescaledb), M1 still runs fully — those are only
needed in M3 (embeddings) and for OHLCV scale.

### SEC EDGAR ingestion (`backend/app/ingestion/sec_edgar.py`)
- **Fair-access compliant:** validates a real `User-Agent` (must contain an email,
  rejects placeholders) *before* any request; rate-limited to `< sec_max_rps`
  (default 8/s); exponential backoff on 429/5xx/network via `tenacity`.
- Endpoints: `company_tickers.json` (ticker→CIK), `submissions/CIK#.json`,
  `api/xbrl/companyfacts/CIK#.json`.
- **Provenance** on every payload: `source_url`, `retrieved_at`, sha256
  `content_hash`; raw JSON cached under `data/cache/sec/`.
- Pure parsers: `parse_company_meta`, `parse_recent_filings` (form filter),
  `parse_facts` (flatten XBRL units → datapoints).

### Price ingestion (`backend/app/ingestion/prices.py`)
- `PriceProvider` protocol + free `StooqProvider` (no API key). Factory
  `get_price_provider()`.
- **Non-blocking by design:** a price failure is soft — bootstrap logs it and
  continues. SEC data is the source of truth.

### DB layer (`backend/app/db/`)
- `session.py` — psycopg3 connection + `transaction()` context + `ping()`.
- `repo.py` — idempotent upserts (`ON CONFLICT`) for company, ticker, exchange,
  raw_documents (dedup on `content_hash`), filings, bulk facts, bulk prices.

### Bootstrap (`scripts/bootstrap_ticker.py`)
`python scripts/bootstrap_ticker.py PLTR [--dry-run] [--no-cache] [--max-facts N]`
Resolve CIK → fetch submissions + companyfacts → parse → prices (soft) → persist
(unless `--dry-run`) → clean summary (company, CIK, latest 10-K/10-Q, #facts,
#filings, provenance hashes).

### Tests (`backend/tests/`) — 30 passing
migration presence/order/guards · UA validation · CIK normalization · content
hashing · XBRL parsing · **bootstrap dry-run with no DB access** (DB pointed at an
unroutable host, still returns 0).

---

## 2. How to run

```bash
# Postgres must be running (local or docker compose up -d postgres).
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                       # or: pip install psycopg[binary] httpx tenacity pydantic-settings pytest

# configure
export ASTERION_DB_HOST=localhost ASTERION_DB_NAME=asterion ASTERION_DB_USER=<you>
export ASTERION_SEC_USER_AGENT="Your Name (you@email.com)"   # SEC requires a real email

python ../scripts/migrate.py --status         # list migrations
python ../scripts/migrate.py                  # apply
python ../scripts/bootstrap_ticker.py PLTR --dry-run   # fetch+parse, no writes
python ../scripts/bootstrap_ticker.py PLTR             # ingest into Postgres
python -m pytest -q                            # 30 tests
```

## 3. Verified result for PLTR (live run)

```
Company   : Palantir Technologies Inc.
CIK       : 0001321655    SIC 7372 (Prepackaged Software)   Nasdaq
Latest 10-K: 2026-02-17 (0001321655-26-000011)
Latest 10-Q: 2026-05-05 (0001321655-26-000028)
Filings    : 65 (10-K/10-Q/8-K)
XBRL facts : 7560 parsed → 6832 distinct rows stored
Idempotent : re-run leaves counts unchanged (6832)
```
Sanity check (not a computed metric — raw stored fact): FY2025 `Revenues` =
4,475,446,000 USD, period_end 2025-12-31, from the 2026 10-K.

## 4. Known limitations

1. **Stooq price gating.** Stooq now demands an API key from some IPs/datacenters;
   the price fetch soft-fails (`prices=0`) and ingestion continues. On a normal
   home IP it usually works. Swap in a paid provider later (same interface). No
   adjusted-close from Stooq — close is mirrored into `adj_close`.
2. **No pgvector / timescaledb on the local Homebrew PG.** Guarded out; embeddings
   (M3) and hypertable conversion need the extensions (present in the
   `timescaledb-ha` Docker image).
3. **Facts dedup key uses `NULLS NOT DISTINCT`** (PG15+). On PG <15 facts with a
   NULL `fiscal_period`/`accession_number` could duplicate on re-ingest.
4. **`financial_ratios`, `shares_outstanding_history`, `valuation_multiples`,
   `document_chunks` are created but not populated** — that is M2/M3 work.
5. **Extensions require superuser** for `CREATE EXTENSION` on first migrate.
6. Filings index is captured; filing **document bodies** (10-K text) are not yet
   downloaded/chunked — that is M3 (RAG).

## 5. Next step — M2 (Quant core)

Compute deterministic ratios from `financial_facts` into `financial_ratios`
(pure Python, typed, unit-tested, missing-data aware): margins, ROIC/ROE, FCF
yield, DuPont, Altman Z, Piotroski F, Beneish M, dilution (SBC/OCF), Rule of 40.
Then the first sector-relative scorecard for PLTR — still no LLM, still no UI.
