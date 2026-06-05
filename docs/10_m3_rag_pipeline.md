# M3: RAG Pipeline

The M3 milestone successfully introduced the Retrieval-Augmented Generation (RAG) pipeline to Asterion, operating over local SEC filings. The pipeline downloads 10-K and 10-Q filings, parses them into semantic sections, splits them into manageable chunks, generates local embeddings (where supported), and offers a robust BM25 + Vector hybrid search engine.

## What Was Implemented

1. **Document Ingestion:** Extended `sec_edgar.py` to natively download raw HTML and TXT filing documents directly from the SEC Archives via `https://www.sec.gov/Archives/edgar/data/...`.
2. **Section Extraction:** Added `sec_filing_sections.py` and `document_parser.py` (utilizing `BeautifulSoup`) to cleanly extract text from complex SEC HTML and identify standard sections like "Item 1. Business" and "Item 1A. Risk Factors".
3. **Chunking Engine:** Developed `chunking.py` for sliding-window chunking (default 1500 chars, 200 overlap). The chunking is section-aware and preserves critical provenance metadata for each chunk (`accession_number`, `filing_date`, `section_name`).
4. **Local Embeddings (Ollama):** Created `ollama_provider.py` to seamlessly connect to a local Ollama instance and use `nomic-embed-text` to generate vector embeddings for chunks.
5. **Database Enhancements:** Added `0007_pgvector_embeddings.sql` migration to introduce the `embedding` column. Handled missing `pgvector` extensions with graceful fallback logic.
6. **Hybrid Search:** Built `hybrid_search.py` leveraging Postgres' `websearch_to_tsquery` (BM25) and `vector_cosine_ops` (HNSW). Search results are ranked with configurable weightings for recency and section importance.

## How to Run Filing Ingestion

To ingest SEC filings (such as 10-K and 10-Q) into the database, run:
```bash
# Make sure your User-Agent is defined in .env or passed inline
ASTERION_SEC_USER_AGENT="Asterion AI (your_email@domain.com)" \
.venv/bin/python scripts/ingest_filings.py PLTR --limit 2
```
*Note: Depending on your local setup, the script will output whether it successfully generated Ollama embeddings or gracefully degraded to store chunks without embeddings.*

## How to Run RAG Search

To query the ingested RAG database, run:
```bash
.venv/bin/python scripts/rag_search.py "dilution risk" --ticker PLTR --top-k 5
```
This queries the chunk database and prints beautifully formatted citations including `Source Document`, `Filing Type`, `Filing Date`, and `Section`.

## Extraction & Limitations

- **Sections Extracted:** On standard filings, "Business", "Risk Factors", and "Management's Discussion" are reliably parsed.
- **Limitations:** SEC filings vary wildly in formatting. If the regex parser cannot confidently identify section boundaries (due to complex inline CSS or missing standard headers), it gracefully falls back to capturing the text as a "Full Document" block.
- **Embeddings Fallback:** If `pgvector` is missing in the Postgres DB, or the local Ollama instance cannot be reached, chunk ingestion successfully degrades to a keyword-only architecture, ensuring the BM25 text search pipeline remains entirely functional.

## Next Step: M4

With the deterministic quant foundation (M2) and the RAG document extraction engine (M3) operational, **M4** will introduce the Synthesis and Agentic Planning layer. M4 will combine the deterministic ratio metrics and the retrieved qualitative SEC contexts to automatically generate coherent, institutional-grade equity research memos via local LLMs.
