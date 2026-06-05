# ASTERION — Master Plan

> Local-first, institutional-grade equity intelligence and portfolio decision
> engine for a single developer. Deterministic math is the skeleton; a local LLM
> is the analyst, not the oracle.

---

## 1. What Asterion Is

- A **local-first research operating system** for public-equity investing.
- A **deterministic quantitative engine**: 16 reproducible 0–100 scores computed
  in pure Python from a structured Postgres database — no LLM math, no external
  call at scoring time.
- A **local knowledge library** (investor lenses, formula cards, sector
  playbooks, company profiles, decision playbooks) — the actual "intelligence."
- A **local RAG system** over SEC filings / transcripts / user documents, with
  full citation metadata on every chunk.
- A **local LLM reasoning layer** (Ollama-first) that summarizes, extracts,
  debates bull/bear, applies investor lenses, and writes memos — strictly grounded
  in structured data and retrieved evidence.
- A **decision policy engine** that turns scores + evidence into disciplined,
  risk-bounded actions with explicit thesis-invalidation conditions.
- A **backtesting + evaluation layer** that prevents look-ahead / survivorship
  bias and measures its own predictions (incl. LLM hallucination rate).
- A **dashboard + Telegram alerting** system.

## 2. What Asterion Is NOT

- ❌ Not a fake "AI stock picker" or hype bot.
- ❌ Not a naive buy/sell predictor — every verdict carries confidence, key risks,
  and invalidation conditions.
- ❌ Not a system that lets an LLM invent or calculate numbers.
- ❌ Not a day-trading execution bot — intraday is walled off, experimental, paper-only, capped.
- ❌ Not a pirate library — no copyrighted full text; original summaries + public
  / SEC / user-provided sources only.
- ❌ Not a promise of guaranteed prediction. Markets are noisy, reflexive,
  non-stationary, adversarial. We estimate probability, EV, uncertainty, downside.

## 3. System Architecture

```
                         ┌─────────────────────────────────────────┐
                         │              Next.js Frontend             │
                         │  ticker report · scorecard · RAG search   │
                         │  portfolio risk · journals · backtests    │
                         └───────────────────┬───────────────────────┘
                                             │ HTTP (JSON)
                         ┌───────────────────▼───────────────────────┐
                         │            FastAPI Backend (Python)        │
                         │  api/ → services/ → {quant, rag, llm,      │
                         │  scoring, decision, backtesting}           │
                         └───┬───────────┬───────────┬───────────┬────┘
                             │           │           │           │
          ┌──────────────────▼──┐   ┌────▼─────┐ ┌───▼────┐  ┌───▼─────────┐
          │ PostgreSQL          │   │ pgvector │ │ Ollama │  │ Redis +     │
          │ + TimescaleDB       │   │ (chunks) │ │ (LLM)  │  │ Celery      │
          │ relational + OHLCV  │   └──────────┘ └────────┘  │ workers     │
          └─────────────────────┘                            └───┬─────────┘
                             ▲                                    │
          ┌──────────────────┴────────────────────────────────────▼─────────┐
          │  Ingestion (data pipes only): SEC EDGAR · FRED · OHLCV · news ·  │
          │  user uploads.  Every item: source, url, ts, hash, license.     │
          └──────────────────────────────────────────────────────────────────┘
```

**Layered pipeline (left → right, determinism → narrative):**
1. Ingestion → raw structured data + raw documents (with provenance).
2. Quant engine → deterministic ratios + 16 scores (reproducible, versioned).
3. RAG → evidence packs with citations.
4. LLM analyst committee → memos grounded in (2) + (3), strict JSON.
5. Decision policy engine → bounded action + invalidation + sizing.
6. Alerts + dashboard + backtest feedback.

## 4. Local-First Design

- **All intelligence is local:** Postgres, pgvector, Timescale, document storage,
  knowledge library, RAG, LLM (Ollama / LM Studio / llama.cpp / vLLM via one
  provider interface), quant math in Python.
- **External APIs are data pipes**, never the intelligence core. Disabled-by-
  default external LLM fallback behind an explicit flag.
- **Runs on a normal dev machine.** Default Ollama models chosen to fit ≤ ~16–24GB.
  See `05_local_llm_strategy.md`.

## 5. Data Sources (MVP = free / low-cost only)

| Source | Use | Cost | Constraint |
|--------|-----|------|------------|
| SEC EDGAR (submissions + companyfacts XBRL) | filings, fundamentals | free | <10 req/s, User-Agent (name+email), backoff |
| FRED | macro time series (yield curve, CPI, fed funds) | free | API key |
| One OHLCV provider (swappable: stooq/yfinance-class → paid later) | daily prices | free/low | provider interface |
| User uploads | PDFs, notes | free | user-owned |
| News feed (later) | catalysts/sentiment | tier-2 | dedup required |

Everything behind `ingestion/*` provider interfaces so sources are replaceable.
Paid sources (Alpaca/Polygon/FMP/Finnhub) are post-MVP, same interface.

## 6. Knowledge Library Design

14 libraries (see `02_knowledge_library_overview.md`). Split rule:
- **Structured SQL** = anything numeric, comparable, score-feeding, or audited.
- **Vector documents** = prose: philosophy, summaries, framework cards, filing
  chunks.
- **Never the LLM's job** = the actual numbers, thresholds, or score arithmetic.

Files on disk now: `knowledge/investor_lenses/`, `knowledge/formulas/<cat>/`,
`knowledge/sector_playbooks/`, `knowledge/company_profiles/`,
`knowledge/decision_playbooks/`.

## 7. RAG Design

Hybrid retrieval: pgvector similarity + Postgres full-text (BM25-style tsvector)
+ metadata filter + recency/source-quality/section-importance weighting, then
optional local cross-encoder rerank → evidence pack with citations. Section-aware
chunking; every chunk keeps ticker, document, filing type, fiscal period, date,
section, page, source_url, accession, text_hash. See `03_rag_design.md`,
`04_hybrid_search_strategy.md`, `07_rag_pipeline.md`.

## 8. Local LLM Design

Provider abstraction (`llm/provider_base.py`) over Ollama (primary), LM Studio /
llama.cpp / vLLM (OpenAI-compatible), external API (off by default). Strict JSON,
retries, schema validation, JSON repair, timeouts, token/model/prompt-version
logging, hallucination + citation audit. Analyst committee of 11 agents → Final
Committee Chair. See `05_local_llm_strategy.md`.

## 9. Quant Engine Design

`backend/app/quant/`: fundamentals, valuation, forensic, risk, portfolio,
technicals, regime, catalysts, scoring, normalization, confidence. Pure functions,
typed, unit-tested, missing-data aware. Scores: sector-relative Z→CDF
normalization, stored raw inputs + formula version + confidence + missing penalty
+ explanation + citations. Investment (#15) regime-aware; Trading (#16) walled off.

## 10. Database Design

Postgres + TimescaleDB (OHLCV hypertables) + pgvector + tsvector + JSONB.
Survivorship via `companies.is_active`; historical `score_runs`/`final_scores`
for self-backtesting; pre-computed `financial_ratios`. Full table list and DDL
plan in `06_database_schema.md`; migrations in `backend/app/db/migrations/`.

## 11. MVP Plan

Universe (20): NVDA, GOOGL, META, ASML, V, BLK, PLTR, VRT, MELI, NU, TSM, AMD,
MSFT, AMZN, CRWD, NET, SHOP, LLY, NVO, RKLB. **First ticker: PLTR.**

MVP deliverables: schema · SEC ingestion (US) · daily prices · formula library ·
investor lenses · sector playbooks · local RAG ingest · LLM provider layer ·
one-ticker report · basic scorecard · bull/bear memo · decision policy · Telegram
prototype · backtest skeleton · frontend ticker page.

## 12. Milestones

- **M0 — Foundation (this pass):** docs + repo skeleton + interfaces + compose.
- **M1 — Data spine:** migrations applied; SEC + FRED + OHLCV ingestion for PLTR.
- **M2 — Quant core:** fundamentals/forensic/valuation/risk formulas + tests;
  scorecard for PLTR from real data.
- **M3 — Knowledge + RAG:** investor lenses + sector playbooks + formula cards
  populated; SEC filing chunked/embedded; hybrid search working.
- **M4 — LLM analyst:** Ollama provider; bull/bear + memo for PLTR, audited.
- **M5 — Decision + alerts:** policy engine verdicts; Telegram prototype.
- **M6 — Backtest skeleton:** walk-forward harness with costs/slippage; score-
  bucket evaluation.
- **M7 — Frontend:** ticker report page wired to backend.

## 13. Risks

- Local LLM JSON reliability / reasoning ceiling → strict schema + repair + audit;
  external fallback flag.
- Free data-source quality/coverage gaps → confidence penalties + provider swap.
- Scoring miscalibration → label as heuristic until Brier-calibrated.
- Solo-dev maintenance load → strict modular interfaces, tests, no half-features.
- Over-fitting / data leakage → purged CV, walk-forward, mandatory costs.

## 14. Limitations

- No guaranteed prediction. Final Investment score is a *ranking heuristic* until
  calibrated against realized outcomes.
- Small universe + limited history → Black-Litterman / HMM are experimental,
  behind flags.
- Sentiment from a small local model is noisy and low-weight by design.
- Intraday module is experimental, paper-only, capped.

## 15. Anti-Hype Rules (non-negotiable)

1. No fake prediction claims. 2. No invented numbers. 3. No LLM-calculated ratios.
4. No buy/sell without confidence + risk + invalidation. 5. No mixing investing
and day trading. 6. No pirated/copyrighted full text. 7. Every chunk keeps
citation metadata. 8. Every score reproducible. 9. Every alert cites its source.
10. Every model output logged. 11. Every backtest includes costs + slippage.
12. Every strategy avoids look-ahead bias. 13. Local-first by default.
14. External APIs are pipes, not the brain. 15. The knowledge library is the
engine. 16. The quant engine is the decision skeleton. 17. The LLM is the analyst,
not the oracle.

---

## Final Verdict Taxonomy (extends report's decision matrix)

`strong investment candidate` · `investment candidate` · `starter position only`
· `watchlist` · `wait for better price` · `trading setup only` · `avoid` ·
`reduce` · `exit — thesis broken` · `insufficient data`.

Every verdict ships with: action · confidence (Low/Med/High) · time horizon · max
position size + sizing logic · thesis-invalidation conditions · key risks ·
monitoring triggers · what data is missing.
