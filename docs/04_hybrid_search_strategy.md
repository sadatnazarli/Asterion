# 04 — Hybrid Search Strategy

Trace: `03_rag_design.md` §5. Defines exactly how vector + keyword + metadata +
weighting fuse into a ranked result. All in Postgres (pgvector + tsvector) — no
extra search service.

---

## 1. Why Hybrid

- **Vector** captures semantics ("management tone softened") but misses exact
  tokens (tickers, statute names, "10b5-1", "PDUFA").
- **Keyword (BM25-style)** nails exact tokens but misses paraphrase.
- **Metadata** scopes to the right company/period/section (correctness, not rank).
- Fusing all three beats any single retriever on financial filings.

## 2. Stage Order

```
1. HARD FILTER (SQL WHERE): ticker, document_type, fiscal_period, date range,
   section_name  →  candidate set
2. VECTOR search on candidates: pgvector cosine, top K_v (default 40)
3. KEYWORD search on candidates: tsvector ts_rank_cd, top K_k (default 40)
4. FUSE: Reciprocal Rank Fusion
5. WEIGHT: × recency × source_quality × section_importance
6. RERANK (optional cross-encoder) → final top_k (default 8)
```

## 3. Vector Component

```sql
SELECT chunk_id, 1 - (embedding <=> :qvec) AS cos_sim
FROM document_embeddings e JOIN document_chunks c USING (chunk_id)
WHERE <hard filters>
ORDER BY embedding <=> :qvec
LIMIT :k_v;
```
Index: `ivfflat`/`hnsw` on `embedding vector_cosine_ops`.

## 4. Keyword Component

```sql
SELECT chunk_id,
       ts_rank_cd(c.tsv, websearch_to_tsquery('english', :q)) AS bm25
FROM document_chunks c
WHERE c.tsv @@ websearch_to_tsquery('english', :q)
  AND <hard filters>
ORDER BY bm25 DESC
LIMIT :k_k;
```
Index: GIN on `tsv` (generated `tsvector` column over chunk text).

## 5. Fusion — Reciprocal Rank Fusion (RRF)

For each chunk appearing in either list at rank `r` (1-based):

```
RRF(chunk) = Σ_lists  1 / (k_rrf + rank_in_list)        # k_rrf = 60 default
```

RRF is rank-based (not score-scale-based), so it is robust to vector cosine and
BM25 living on different scales — no normalization headaches.

## 6. Weighting (applied to RRF score)

```
final = RRF × w_recency × w_source × w_section
```

- **w_recency** = exp(−λ · age_days). λ tuned so a ~2-year-old filing ≈ 0.5.
  For "latest" queries λ larger; for "historical change" queries λ→0 (keep old).
- **w_source** = source-quality map (10-K/10-Q > 8-K > presentation > news).
- **w_section** = section-importance map (Risk Factors, MD&A > boilerplate).

Weights are config (`rag` settings), versioned, logged with each retrieval into
`retrieval_results` for reproducibility.

## 7. Special Case — Risk-Factor Diff ("changed between 10-Ks")

Not pure retrieval. Pull Item 1A from the two most recent 10-Ks (metadata
filter), align by subsection, embed sentences, flag low-cosine-match
inserts/deletes (per report §NLP). Output = added/removed risk sentences with
citations. Handled in `evidence_pack.py` as a dedicated builder, not generic search.

## 8. Recency / Quality / Section Maps (defaults)

| Knob | Default |
|------|---------|
| K_v / K_k | 40 / 40 |
| k_rrf | 60 |
| final top_k | 8 |
| recency λ (default queries) | ln(2)/730 per day |
| source_quality | 10-K 1.0 · 10-Q 0.95 · 8-K 0.85 · transcript 0.9 · presentation 0.7 · news 0.6 · user 0.8 |
| section_importance | Risk Factors 1.0 · MD&A 0.95 · segments 0.9 · financial notes 0.85 · boilerplate 0.4 |

## 9. Reproducibility

Every retrieval logs: query, qvec model+dim, filters, K params, weight version,
returned chunk_ids + scores → `rag_queries` + `retrieval_results`. Re-running a
logged query must reproduce ranking given the same corpus state.
