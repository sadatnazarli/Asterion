#!/usr/bin/env python3
import argparse
import sys
import os
import logging
from datetime import datetime

# Add the backend directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.core.config import settings
from app.db.session import get_connection
from app.db.repo import (
    upsert_company,
    upsert_ticker,
    insert_raw_document,
    upsert_filing
)
from app.ingestion.sec_edgar import SECClient, parse_company_meta, parse_recent_filings
from app.rag.document_parser import parse_filing_document
from app.rag.chunking import chunk_sections
from app.rag.embeddings import generate_embeddings, store_chunks

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Ingest SEC filings, parse, chunk, embed, and store.")
    parser.add_argument("ticker", type=str, help="Ticker symbol to ingest (e.g., PLTR)")
    parser.add_argument("--limit", type=int, default=2, help="Number of recent 10-K/10-Q filings to ingest")
    
    args = parser.parse_args()
    ticker = args.ticker.upper()
    
    print(f"Starting ingestion for {ticker} (Limit: {args.limit} filings)")
    
    try:
        with get_connection() as conn:
            with SECClient() as client:
                # 1. Resolve CIK and fetch submissions
                logging.info(f"Resolving CIK for {ticker}...")
                cik = client.resolve_cik(ticker)
                
                logging.info(f"Fetching submissions for CIK {cik}...")
                submissions_res = client.fetch_submissions(cik)
                
                # 2. Setup Company & Ticker in DB
                meta = parse_company_meta(submissions_res.data)
                with conn.transaction():
                    company_id = upsert_company(conn, meta)
                    upsert_ticker(conn, company_id, ticker)
                
                # 3. Find 10-K and 10-Q filings
                filings = parse_recent_filings(submissions_res.data, forms=("10-K", "10-Q"), limit=args.limit)
                if not filings:
                    logging.info("No 10-K or 10-Q filings found.")
                    return
                
                # 4. Ingest each filing
                for f in filings:
                    accession = f["accession_number"]
                    primary_doc = f["primary_doc"]
                    form_type = f["form_type"]
                    filing_date = f["filing_date"]
                    
                    if not primary_doc:
                        logging.warning(f"No primary document for {form_type} {accession}. Skipping.")
                        continue
                        
                    ext = primary_doc.split(".")[-1].lower() if "." in primary_doc else "txt"
                    
                    logging.info(f"Fetching {form_type} document: {primary_doc} ({accession})...")
                    try:
                        doc_res = client.fetch_filing_document(cik, accession, primary_doc)
                    except Exception as e:
                        logging.error(f"Failed to fetch document: {e}")
                        continue
                    
                    # 5. Save Raw Document & Filing
                    with conn.transaction():
                        raw_doc_id = insert_raw_document(
                            conn,
                            company_id=company_id,
                            document_type=form_type,
                            source_name="SEC EDGAR",
                            source_url=doc_res.provenance.source_url,
                            content_hash=doc_res.provenance.content_hash,
                            storage_path=doc_res.provenance.storage_path,
                            accession_number=accession,
                        )
                        upsert_filing(conn, company_id, f, raw_doc_id)
                    
                    # 6. Parse and Chunk
                    logging.info("Parsing document sections...")
                    sections = parse_filing_document(doc_res.raw_bytes, extension=ext)
                    
                    logging.info(f"Extracted {len(sections)} sections. Chunking...")
                    metadata = {
                        "company_id": company_id,
                        "ticker": ticker,
                        "document_type": form_type,
                        "filing_type": form_type,
                        "filing_date": filing_date,
                        "accession_number": accession,
                        "raw_document_id": raw_doc_id,
                    }
                    
                    chunks = chunk_sections(sections, metadata)
                    logging.info(f"Created {len(chunks)} chunks. Generating embeddings...")
                    
                    # 7. Embed and Store
                    chunks = generate_embeddings(chunks)
                    
                    logging.info("Storing chunks to database...")
                    # Note: We'll delete existing chunks for this document to be idempotent
                    with conn.transaction():
                        conn.execute("DELETE FROM document_chunks WHERE raw_document_id = %s", (raw_doc_id,))
                        store_chunks(conn, chunks)
                    
                    logging.info(f"Successfully ingested {form_type} ({accession}).\n")
                    
        print("\nIngestion complete.")
                
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
