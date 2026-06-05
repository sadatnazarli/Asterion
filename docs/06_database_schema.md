# 06 — Database Schema

Trace: `MASTER_PLAN.md` §10, Phase 7, report §"Database Schema Architecture"
(17-table baseline → expanded). Postgres 16 + TimescaleDB + pgvector + tsvector +
JSONB. Migrations: `backend/app/db/migrations/` (raw SQL, ordered, idempotent).

Non-negotiables baked in:
- **Survivorship** — `companies.is_active`, delisted rows retained.
- **Self-backtest** — historical `score_runs`/`final_scores` never overwritten.
- **Pre-computed `financial_ratios`** — minimize runtime compute.
- **Provenance** — every ingested row carries source/url/ts/hash/license.
- **Walled garden** — investing vs trading split at table level.

Conventions: `snake_case`; surrogate `id BIGINT GENERATED ALWAYS AS IDENTITY`
unless a natural PK is clearer; `created_at/updated_at timestamptz default now()`;
FKs `on delete restrict` for reference data; JSONB for flexible blobs; every
table has a `COMMENT` (name them with the Asterion convention).

---

## Schema Groups & Tables

### Core
| Table | PK | Key columns | Writes | Reads |
|-------|----|-----|--------|-------|
| `exchanges` | id | code, name, country, mic | seed | companies |
| `sectors` | id | gics_code, name | seed (GICS) | normalization |
| `industries` | id | gics_code, name, sector_id→sectors | seed | normalization |
| `companies` | id | cik (uniq), name, sector_id, industry_id, country, **is_active**, market_cap, first_seen, delisted_at | ingestion(sec) | everything |
| `tickers` | id | company_id→companies, symbol, exchange_id, is_primary, active_from, active_to | ingestion | mapping (symbol changes/dual listings) |

### Market Data (TimescaleDB hypertables)
| Table | PK | Columns | Notes |
|-------|----|---------|------|
| `prices_daily` | (ticker_id,date) | open,high,low,close,adj_close,volume,vwap | hypertable on `date`; survivorship-safe |
| `prices_intraday` | (ticker_id,ts) | o,h,l,c,volume,vwap | hypertable; **trading module only** |
| `market_snapshots` | id | ticker_id, asof, market_cap, shares, float, short_interest | daily snapshot |
| `technical_indicators` | (ticker_id,date,name) | value, params jsonb, formula_version | computed by quant (not stored from API) |

### Fundamentals
| Table | PK | Columns | Notes |
|-------|----|---------|------|
| `financial_statements` | id | company_id, period_end, fiscal_period, form_type, currency, raw jsonb | one row per statement filing |
| `financial_facts` | id | company_id, concept(xbrl tag), period_end, fiscal_period, value, unit, accession_number, source_url, retrieved_at, content_hash | normalized XBRL facts (EDGAR companyfacts) |
| `financial_ratios` | (company_id,period_end,name) | value, formula_version, inputs jsonb, confidence, missing_penalty | **pre-computed by quant**; deterministic |
| `shares_outstanding_history` | (company_id,period_end) | basic, diluted, source | dilution analysis |
| `valuation_multiples` | (company_id,date,name) | value, percentile_sector, formula_version | EV/EBITDA etc + sector pctl |

### Documents / RAG
| Table | PK | Columns | Notes |
|-------|----|---------|------|
| `raw_documents` | id | company_id, document_type, source_name, source_url, retrieved_at, content_hash(uniq), license_note, storage_path, accession_number | provenance anchor |
| `filings` | id | company_id, accession_number(uniq), form_type, filing_date, period_of_report, primary_doc_url | SEC index |
| `transcripts` | id | company_id, event_date, quarter, source, raw_document_id | earnings calls |
| `investor_presentations` | id | company_id, event_date, raw_document_id | |
| `shareholder_letters` | id | company_id, year, raw_document_id, license_note | legally-available only |
| `document_chunks` | id | raw_document_id, company_id, ticker, document_type, filing_type, fiscal_period, filing_date, section_name, page_number, text, tsv tsvector(generated), text_hash | section-aware chunks |
| `document_embeddings` | chunk_id→document_chunks | embedding vector(N), embed_model, embed_dim | pgvector; N=`ASTERION_EMBED_DIM` |
| `source_citations` | id | chunk_id, ticker, document_type, filing_date, section, accession_number, source_url, char_span int4range | attached to outputs/alerts |

### Events
| Table | PK | Columns |
|-------|----|---------|
| `news_events` | id | company_id, published_at, source, url, title, dedup_hash, importance, sentiment, raw_document_id |
| `catalysts` | id | company_id, event_date, event_type, description, importance_weight(0.1–1.0), source_url |
| `earnings_events` | id | company_id, event_date, period, eps_est, eps_actual, hist_iv_crush |
| `sec_events` | id | company_id, filing_id→filings, event_type |
| `insider_trades` | id | company_id, person, role, txn_date, txn_code, is_10b5_1, shares, price, source_url |
| `institutional_holdings` | id | company_id, holder, asof(13F), shares, delta_shares, source_url |
| `fda_events` | id | company_id, event_date, event_type(PDUFA…), drug, phase, source_url |

### Knowledge (JSON files = canonical; SQL mirrors for audit/query)
| Table | PK | Columns |
|-------|----|---------|
| `investor_lenses` | slug | name, style, data jsonb, embedding vector(N), version |
| `formula_cards` | slug | category, name, data jsonb, python_function_name, version |
| `sector_playbooks` | slug | sector_name, data jsonb, scoring_adjustments jsonb, version |
| `decision_playbooks` | slug | data jsonb (rules), version |
| `company_knowledge_profiles` | company_id | profile jsonb, last_updated |
| `regime_definitions` | id | name, rule jsonb, score_weights jsonb, is_experimental |

### Scoring (historical, append-only)
| Table | PK | Columns |
|-------|----|---------|
| `score_runs` | id | company_id, asof, regime_id, formula_bundle_version, created_at | one scoring pass |
| `factor_scores` | id | run_id→score_runs, score_name, value(0–100), raw_inputs jsonb, confidence, missing_penalty, sector_percentile |
| `final_scores` | id | run_id, final_investment_score, final_trading_score, regime_id, confidence, verdict | walled: invest vs trade separate columns |
| `score_explanations` | id | run_id, score_name, explanation_text, citations jsonb | LLM/templated prose, audited |

### Portfolio
| Table | PK | Columns |
|-------|----|---------|
| `portfolios` | id | name, base_currency, created_at |
| `portfolio_positions` | id | portfolio_id, company_id, entry_price, position_size, kelly_fraction, atr_stop_loss, opened_at, closed_at, thesis_id |
| `portfolio_snapshots` | id | portfolio_id, asof, nav, weights jsonb |
| `portfolio_risk_metrics` | id | portfolio_id, asof, var95, cvar95, beta, max_dd, sector_concentration jsonb |
| `allocation_recommendations` | id | portfolio_id, company_id, asof, target_weight, method(BL/vol/kelly), rationale, sizing_logic |

### Trading (walled garden — experimental, paper-only)
| Table | PK | Columns |
|-------|----|---------|
| `trade_setups` | id | company_id, asof, setup_type, rvol, gap_pct, float, vwap_dist, atr_stop, bias, experimental(bool default true) |
| `trade_journal` | id | company_id, entry_ts, exit_ts, entry_logic, exit_logic, slippage, psych_notes, pnl |
| `paper_trades` | id | company_id, entry_ts, qty, entry_price, exit_ts, exit_price, fees, slippage |
| `execution_assumptions` | id | name, slippage_model jsonb, cost_model jsonb, version |

### Backtesting
| Table | PK | Columns |
|-------|----|---------|
| `strategies` | id | name, spec jsonb, version |
| `backtest_runs` | id | strategy_id, start, end, cost_model, slippage_model, cv_method, sharpe, sortino, calmar, max_dd, win_rate, expectancy |
| `backtest_trades` | id | run_id, company_id, entry_ts, exit_ts, side, pnl, fees, slippage |
| `signal_performance` | id | signal_name, bucket, horizon_days, avg_return, hit_rate, n |
| `model_predictions` | id | model_name, company_id, asof, prediction jsonb, horizon_days |
| `prediction_outcomes` | id | prediction_id, realized jsonb, brier, correct |

### AI / RAG ops
| Table | PK | Columns |
|-------|----|---------|
| `rag_queries` | id | query_text, qvec_model, qvec_dim, filters jsonb, weight_version, created_at |
| `retrieval_results` | id | rag_query_id, chunk_id, vector_rank, keyword_rank, rrf, final_score |
| `model_calls` | id | task, model_name, prompt_version, tokens_in, tokens_out, latency_ms, temperature, created_at |
| `llm_outputs` | id | model_call_id, raw_output, parsed jsonb, schema_valid(bool) |
| `hallucination_audits` | id | llm_output_id, flagged_numbers jsonb, uncited_claims jsonb, passed(bool) |
| `prompt_templates` | id | task, version, template_text, schema jsonb |

### Alerts
| Table | PK | Columns |
|-------|----|---------|
| `alert_rules` | id | name, rule jsonb, severity, enabled |
| `alerts` | id | company_id, alert_type, severity, reason, source_url, confidence, what_to_check, report_link, created_at |
| `alert_deliveries` | id | alert_id, channel(telegram), delivered_at, status |

### User Memory
| Table | PK | Columns |
|-------|----|---------|
| `watchlists` | id | name, company_ids bigint[] |
| `investment_journal` | id | company_id, thesis, decision, rationale, entry_asof, outcome, closed_asof |
| `mistake_patterns` | id | pattern_name, description, trigger_conditions jsonb |
| `user_decision_feedback` | id | company_id, run_id, user_action, agreed(bool), notes, created_at |

---

## Index Plan (highlights)
- `prices_daily` / `prices_intraday`: Timescale hypertable (time partition) +
  index `(ticker_id, date desc)`.
- `financial_facts`: `(company_id, concept, period_end)`; unique
  `(company_id, concept, period_end, accession_number)`.
- `document_chunks.tsv`: **GIN**. `document_embeddings.embedding`: **HNSW**
  (`vector_cosine_ops`).
- `companies`: index on `is_active`, `cik` unique.
- `score_runs (company_id, asof)`, `final_scores (run_id)`.
- `news_events.dedup_hash` unique (syndication dedup).
- `insider_trades (company_id, txn_date)`, `is_10b5_1` filter.

## Migration Strategy
Plain numbered SQL files (`0001_extensions.sql`, `0002_core.sql`, …) applied by a
tiny runner (`scripts/migrate.py`). Idempotent (`create ... if not exists`).
Extensions first: `timescaledb`, `vector`, `pg_trgm`. Embedding dimension is
templated from `ASTERION_EMBED_DIM` at migration time. Full DDL is implemented in
M1, not in this foundation pass — this doc is the contract.
