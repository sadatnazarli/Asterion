# 07 — RAG Pipeline (implementation contract)

Trace: `03_rag_design.md`, `04_hybrid_search_strategy.md`. This doc fixes the
module interfaces in `backend/app/rag/` so M3 implementation has no ambiguity.

---

## Module Interfaces

### `chunking.py`
```python
def parse_document(raw: RawDocument) -> ParsedDocument: ...
def clean(text: str) -> str: ...                      # strip XBRL noise, dedupe ws
def section_split(doc: ParsedDocument) -> list[Section]: ...   # Item 1A, Item 7…
def chunk(sections: list[Section], *, target_tokens=1000,
          overlap=0.15) -> list[Chunk]: ...           # never split mid-sentence
```
`Chunk` carries all required metadata (see `03` §3) + a contextual header.

### `embeddings.py`
```python
class Embedder(Protocol):
    model: str; dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...
def get_embedder() -> Embedder: ...   # Ollama nomic-embed-text by default
def embed_and_store(chunks: list[Chunk]) -> None: ...  # writes document_embeddings
```

### `hybrid_search.py`
```python
@dataclass
class SearchFilters:
    ticker: str | None=None; document_type: str | None=None
    fiscal_period: str | None=None; date_from=None; date_to=None
    section_name: str | None=None

def vector_search(qvec, filters, k_v=40) -> list[Hit]: ...
def keyword_search(q, filters, k_k=40) -> list[Hit]: ...
def rrf_fuse(*lists, k_rrf=60) -> list[FusedHit]: ...
def apply_weights(hits, *, recency_lambda, source_map,
                  section_map) -> list[FusedHit]: ...
def search(q: str, filters: SearchFilters, top_k=8) -> list[FusedHit]: ...
```
`search` logs to `rag_queries` + `retrieval_results`.

### `rerank.py`
```python
def rerank(q: str, hits: list[FusedHit], top_k=8) -> list[FusedHit]: ...
# local cross-encoder (bge-reranker); no-op passthrough if disabled/unavailable
```

### `evidence_pack.py`
```python
def build_evidence_pack(ticker: str, question: str, *,
                        structured_refs: list[str]) -> EvidencePack: ...
def build_risk_factor_diff(ticker: str) -> RiskFactorDiff: ...  # special builder
```
`EvidencePack` = `{question, chunks:[{text, citation}], structured_refs}`. This is
the ONLY context the LLM may use; numbers outside it are flagged.

### `citations.py`
```python
def to_citation(chunk: Chunk) -> Citation: ...        # writes source_citations
def format_citation(c: Citation) -> str: ...          # human/UI string
```

---

## End-to-End Sequence (ingest → query)

```
ingest:  raw_documents row  →  chunking  →  document_chunks (+tsv)
                            →  embeddings →  document_embeddings
query:   question  →  embed(q)  →  vector_search ∥ keyword_search
                  →  rrf_fuse  →  apply_weights  →  rerank
                  →  build_evidence_pack  →  LLM (grounded, cited)
```

## Determinism & Logging
- Same corpus + same query + same weight version ⇒ same ranking.
- Every retrieval persists params + results (reproducibility, `04` §9).
- Re-embedding (model change) records `embed_model`/`embed_dim` per row; mixed
  dims are never compared.

## Failure Modes Handled
- Empty candidate set after hard filter → return empty pack + reason (no
  hallucinated fallback).
- Embedder/reranker unavailable → degrade (keyword-only / RRF order) + log.
- Oversized filing → section-first chunking keeps Risk Factors retrievable
  without embedding the whole doc at once.

## Evaluation Hooks
Labeled query set (the 9 target queries in `03` §9 + more) → measure retrieval
hit-rate, citation accuracy, hallucination rate. Wired in
`08_backtesting_and_evaluation.md`.
