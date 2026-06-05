# 01 — Local-First Architecture

Trace: implements `00_gemini_report_extracted_requirements.md` §3, §9 and
`MASTER_PLAN.md` §3–4. Scope decision for this build: **Ollama is the local LLM**.

---

## 1. Design Goals

1. **Local-first by default** — all intelligence (DB, vectors, RAG, LLM, math)
   runs on the dev machine. External APIs ingest data only.
2. **Deterministic before AI** — numeric truth comes from SQL + Python; the LLM
   is the last stage and never sources numbers.
3. **Runs on a normal dev machine** — target ≤ 24GB RAM; degrade gracefully on 16GB.
4. **Swappable everything** — data providers and LLM backends behind interfaces.
5. **Reproducible** — versioned formulas, logged model calls, deterministic scores.

## 2. Component Stack

| Layer | Choice | Why | Local? |
|-------|--------|-----|--------|
| Frontend | Next.js + TypeScript | SSR dashboards, charting (Lightweight Charts) | yes |
| API | FastAPI (Python 3.11+) | quant ecosystem dependency | yes |
| Relational DB | PostgreSQL 16 | core store | yes |
| Time-series | TimescaleDB extension | OHLCV hypertables | yes |
| Vectors | pgvector extension | filing/embedding store, one DB to run | yes |
| Full-text | Postgres `tsvector` + GIN | BM25-style keyword search, no extra service | yes |
| Queue/broker | Redis + Celery | async ingestion/scoring/alerts | yes |
| LLM runtime | **Ollama** (primary) | simplest local install, present on this machine | yes |
| LLM (alt) | LM Studio / llama.cpp / vLLM (OpenAI-compatible) | swappable via one interface | yes |
| Embeddings | Ollama embedding model (e.g. `nomic-embed-text`) or `bge-*` via sentence-transformers | local | yes |
| Alerts | Telegram Bot API | mobile push | API pipe |

**One-database principle:** Postgres hosts relational + Timescale + pgvector +
tsvector. Fewer moving parts for a solo dev; can split later if needed.

## 3. Process / Deployment Topology

```
docker-compose (local dev):
  ├── postgres        (timescaledb + pgvector image)
  ├── redis
  ├── backend  (FastAPI, uvicorn)        — depends_on postgres, redis
  ├── worker   (Celery)                  — depends_on postgres, redis
  ├── beat     (Celery scheduler)        — periodic ingestion
  └── frontend (Next.js dev)             — talks to backend

host machine:
  └── Ollama  (runs natively, GPU/Metal) — backend reaches it at host.docker.internal:11434
```

Ollama runs on the host (Metal acceleration on this macOS machine), not in a
container — containers can't reach Apple GPU. Backend reaches it via
`OLLAMA_BASE_URL` (default `http://localhost:11434`, or `host.docker.internal`).

## 4. Backend Module Map

```
backend/app/
  core/            config (pydantic-settings), logging, db session, security
  api/routes/      FastAPI routers (tickers, search, scores, portfolio, alerts)
  db/migrations/   SQL migrations (raw SQL, idempotent, ordered)
  ingestion/       sec_edgar, prices, fred, news, documents, transcripts
  quant/           fundamentals, valuation, forensic, risk, portfolio,
                   technicals, regime, catalysts, normalization, confidence
    formulas/      one module per formula family (pure functions + tests)
  scoring/         16 score builders + ensemble + explanation
  rag/             chunking, embeddings, hybrid_search, rerank, evidence_pack,
                   citations
  llm/             provider_base, ollama_provider, openai_compatible_local_provider,
                   router, json_repair, prompts/
  decision/        policy engine (scores+evidence → bounded action)
  backtesting/     walk-forward harness, costs/slippage, evaluation
  services/        orchestration (build ticker report, run committee)
```

**Dependency direction (must hold):**
`api → services → {quant, rag, llm, scoring, decision, backtesting} → core/db`.
Quant never imports llm. Scoring never imports llm. LLM never writes scores.

## 5. Data Flow — One Ticker Report

1. `ingestion` populates `companies`, `prices_daily`, `financial_facts`,
   `filings`, `raw_documents` (with provenance + hash).
2. `quant` computes `financial_ratios`; `scoring` builds `factor_scores` +
   `final_scores` (sector-normalized, versioned, with confidence). **No LLM.**
3. `rag` builds an evidence pack for the ticker (risk factors, tone, segments).
4. `llm` committee consumes scores (2) + evidence (3) → bull/bear/lens/memo,
   strict JSON, every number audited against (2)/(3).
5. `decision` maps scores + memo → verdict + sizing + invalidation.
6. `services` assembles the report; `alerts` fire on deterministic triggers.

## 6. Configuration & Secrets

`backend/app/core/config.py` (pydantic-settings) reads `.env`. No secret in code.
`.env.example` enumerates every variable. External LLM disabled unless
`ASTERION_ALLOW_EXTERNAL_LLM=true`.

## 7. Hardware Targets

| Profile | RAM | Models | Notes |
|---------|-----|--------|-------|
| Minimum | 16GB | 7–8B Q4 + small embed | slower memos; quant unaffected |
| Recommended | 24–32GB | 8–14B Q4/Q5 + embed | committee viable |
| Comfortable | 48GB+ / dGPU | 14–32B | full committee, longer context |

Quant + DB + RAG retrieval run fine on the minimum profile; only LLM reasoning
scales with hardware. If local reasoning is insufficient for the final memo, the
external-fallback flag exists — architecture stays local-first.

## 8. Why Not Alternatives (brief)

- **Separate vector DB (Qdrant/Weaviate)** — extra service; pgvector keeps it to
  one DB and supports the hybrid-search join with relational filters natively.
- **Deep nets for tabular fundamentals** — report + literature favor tree
  ensembles; not in foundation scope anyway.
- **Cloud LLM as core** — violates local-first; allowed only as off-by-default
  fallback.
