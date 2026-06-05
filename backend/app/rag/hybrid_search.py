import json
from typing import List, Dict, Any, Optional
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel

from .citations import Citation
from .evidence_pack import EvidencePack

# Section importance weights for ranking boost
SECTION_WEIGHTS = {
    "Risk Factors": 1.5,
    "Management's Discussion and Analysis": 1.5,
    "Business": 1.2,
    "Financial Statements": 1.2
}

def hybrid_search(
    conn,
    query: str,
    query_embedding: Optional[List[float]] = None,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 10
) -> List[EvidencePack]:
    """
    Perform hybrid search (BM25 + Vector Similarity if available) over document_chunks.
    Applies section-based boosting and recency weighting.
    """
    filters = filters or {}
    
    # Check if vector search is possible (table has 'embedding' column and we have query_embedding)
    has_vector = False
    if query_embedding:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='document_chunks' AND column_name='embedding';
                """)
                if cursor.fetchone():
                    has_vector = True
        except Exception:
            conn.rollback()
    
    # Base query combining BM25 and Vector score
    # We use websearch_to_tsquery for natural language-friendly BM25
    query_params = {
        "query": query,
        "limit": top_k
    }
    
    where_clauses = []
    
    # Apply filters
    if "ticker" in filters and filters["ticker"]:
        where_clauses.append("ticker = %(ticker)s")
        query_params["ticker"] = filters["ticker"]
        
    if "filing_type" in filters and filters["filing_type"]:
        where_clauses.append("filing_type = %(filing_type)s")
        query_params["filing_type"] = filters["filing_type"]
        
    if "section_name" in filters and filters["section_name"]:
        where_clauses.append("section_name = %(section_name)s")
        query_params["section_name"] = filters["section_name"]
        
    if "start_date" in filters and filters["start_date"]:
        where_clauses.append("filing_date >= %(start_date)s")
        query_params["start_date"] = filters["start_date"]
        
    if "end_date" in filters and filters["end_date"]:
        where_clauses.append("filing_date <= %(end_date)s")
        query_params["end_date"] = filters["end_date"]
        
    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = f" AND {where_sql}"
        
    if has_vector:
        query_params["embedding"] = str(query_embedding)
        
        sql = f"""
        WITH text_search AS (
            SELECT 
                id, ticker, document_type, filing_type, filing_date, section_name, accession_number, text,
                ts_rank(tsv, websearch_to_tsquery('english', %(query)s)) as bm25_score
            FROM document_chunks
            WHERE tsv @@ websearch_to_tsquery('english', %(query)s) {where_sql}
        ),
        vector_search AS (
            SELECT 
                id, ticker, document_type, filing_type, filing_date, section_name, accession_number, text,
                1 - (embedding <=> %(embedding)s::vector) as vector_score
            FROM document_chunks
            WHERE 1=1 {where_sql}
            ORDER BY embedding <=> %(embedding)s::vector
            LIMIT %(limit)s * 2
        ),
        combined AS (
            SELECT 
                COALESCE(t.id, v.id) as id,
                COALESCE(t.ticker, v.ticker) as ticker,
                COALESCE(t.document_type, v.document_type) as document_type,
                COALESCE(t.filing_type, v.filing_type) as filing_type,
                COALESCE(t.filing_date, v.filing_date) as filing_date,
                COALESCE(t.section_name, v.section_name) as section_name,
                COALESCE(t.accession_number, v.accession_number) as accession_number,
                COALESCE(t.text, v.text) as text,
                COALESCE(t.bm25_score, 0) as bm25_score,
                COALESCE(v.vector_score, 0) as vector_score
            FROM text_search t
            FULL OUTER JOIN vector_search v ON t.id = v.id
        )
        SELECT *, 
            (bm25_score * 0.3 + vector_score * 0.7) as base_score
        FROM combined
        """
    else:
        sql = f"""
        SELECT 
            id, ticker, document_type, filing_type, filing_date, section_name, accession_number, text,
            ts_rank(tsv, websearch_to_tsquery('english', %(query)s)) as base_score
        FROM document_chunks
        WHERE tsv @@ websearch_to_tsquery('english', %(query)s) {where_sql}
        """

    # Wrap to apply weights and order
    final_sql = f"""
        WITH results AS (
            {sql}
        )
        SELECT *
        FROM results
        ORDER BY base_score DESC
        LIMIT %(limit)s
    """
    
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(final_sql, query_params)
        rows = cursor.fetchall()
        
    evidence_packs = []
    for row in rows:
        # Apply section weight locally for simplicity, though could be done in SQL
        section_weight = 1.0
        if row['section_name']:
            for key, weight in SECTION_WEIGHTS.items():
                if key.lower() in row['section_name'].lower():
                    section_weight = weight
                    break
        
        # Calculate final score (base_score * section_weight)
        final_score = float(row['base_score']) * section_weight
        
        citation = Citation(
            source_document=f"{row['ticker']}-{row['filing_date'].year}-{row['filing_type']}" if row['filing_date'] else f"{row['ticker']}-{row['filing_type']}",
            filing_type=row['filing_type'] or "Unknown",
            filing_date=row['filing_date'],
            section=row['section_name'],
            accession_number=row['accession_number'] or "Unknown",
            chunk_id=str(row['id'])
        )
        
        ep = EvidencePack(
            text=row['text'],
            citation=citation,
            score=final_score
        )
        evidence_packs.append(ep)
        
    # Re-sort by final score after weights
    evidence_packs.sort(key=lambda x: x.score, reverse=True)
    return evidence_packs[:top_k]
