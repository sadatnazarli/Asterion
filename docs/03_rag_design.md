# 03 — RAG Design

Trace: `MASTER_PLAN.md` §7, Phase 9. Not naive RAG. Every chunk keeps full
citation metadata; the LLM may only reason over retrieved, cited evidence.

---

## 1. Pipeline (stages)

```
raw doc → parse → clean → section-aware chunk → contextual metadata
        → embed → store(pgvector + tsvector) → hybrid retrieve
        → rerank → evidence pack (+ citations)
```

Implemented across `backend/app/rag/`:
`chunking.py · embeddings.py · hybrid_search.py · rerank.py · evidence_pack.py ·
citations.py`. Pipeline doc: `07_rag_pipeline.md`.

## 2. Document Types & Sources

10-K, 10-Q, 8-K, 13F, Form 4 (SEC EDGAR); earnings transcripts (legal sources);
investor presentations; shareholder letters (legally available); user uploads.
Each stored in `raw_documents` with `source_name, source_url, retrieved_at,
content_hash, license_note, accession_number`.

## 3. Chunking Strategy

- **Section-aware**: split on filing structure (Item 1A Risk Factors, Item 7
  MD&A, segment notes) before size-based splitting. Section boundaries preserved.
- Target ~800–1200 tokens, ~15% overlap; never split mid-sentence.
- **Contextual metadata** prepended to each chunk's stored text (a short header:
  ticker, form type, period, section) to improve retrieval grounding.

### Required chunk metadata (every chunk)
`ticker · company_id · document_id · document_type · filing_type ·
fiscal_period · filing_date · section_name · page_number? · source_url ·
accession_number? · text_hash`.

Stored in `document_chunks` (text + metadata) and `document_embeddings` (vector),
joined to `filings`/`raw_documents`.

## 4. Embeddings

Default `nomic-embed-text` via Ollama (dim 768) — see `05`. pgvector column sized
to `ASTERION_EMBED_DIM`. Swappable to `bge-m3` etc.; changing the model requires a
re-embed migration (embedding model + dim recorded per row for safety).

## 5. Hybrid Retrieval

Combine, then fuse:
1. **Vector** — pgvector cosine top-K.
2. **Keyword** — Postgres `tsvector` / `websearch_to_tsquery` (BM25-style) top-K.
3. **Metadata filter** — ticker, document_type, fiscal_period, date range,
   section (hard filters applied before fusion).
4. **Weighting** — recency, source quality, section importance (e.g. Risk Factors
   > boilerplate).

Fusion: Reciprocal Rank Fusion (RRF) over vector + keyword lists, then apply
weight multipliers. Details + formula in `04_hybrid_search_strategy.md`.

## 6. Reranking

Optional local cross-encoder (`bge-reranker` class) over the fused top-N → final
top-k. If unavailable, RRF order is used. Reranker behind a flag; never required.

## 7. Evidence Pack

The unit handed to the LLM. Contains: the query, the final top-k chunks (text +
full citation metadata), and structured-data references (which score/ratio fields
are relevant). The LLM is instructed: **use only this pack**; any number not in
the pack or structured refs is hallucinated and will be flagged.

## 8. Citations

`citations.py` turns each used chunk into a citation: `{ticker, document_type,
filing_date, section, accession_number, source_url, char_span}`. Stored in
`source_citations`, attached to every LLM output and every alert.

## 9. Target Queries (must work)

- "NVDA China export restriction risk"
- "PLTR dilution and SBC trend"
- "MELI FX risk Argentina/Brazil"
- "ASML semiconductor cycle risk"
- "LLY obesity drug catalyst"
- "biotech cash runway and FDA catalyst"
- "management tone changed last earnings call"
- "risk factor changed between 10-Ks" (diff use case — see `04` §recency)

## 10. Evaluation

RAG quality measured in `08_backtesting_and_evaluation.md`: retrieval
hit-rate on labeled queries, citation accuracy, and LLM hallucination rate on
evidence packs. No RAG output is trusted until these are measured.
