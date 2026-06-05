from typing import Dict, Any, List
from psycopg.rows import dict_row
from app.rag.hybrid_search import hybrid_search

EXPECTED_RATIOS = [
    "gross_margin", "operating_margin", "net_margin",
    "roe", "roa", "roic",
    "current_ratio", "quick_ratio", "debt_to_equity",
    "fcf_yield", "revenue_growth_yoy", "eps_growth_yoy"
]

RAG_QUERIES = [
    "business model",
    "risk factors",
    "dilution risk",
    "revenue growth drivers",
    "customer concentration",
    "operating margin",
    "cash flow",
    "stock-based compensation",
    "legal/regulatory risk",
    "macro/interest rate risk"
]

def build_evidence_pack(conn, ticker: str) -> Dict[str, Any]:
    evidence_pack = {
        "ticker": ticker,
        "financial_ratios": {},
        "missing_ratios": [],
        "rag_chunks": {}
    }
    
    # 1. Fetch latest financial ratios
    # First get company_id
    company_id = None
    with conn.cursor() as cursor:
        cursor.execute("SELECT company_id FROM tickers WHERE symbol = %s", (ticker,))
        res = cursor.fetchone()
        if res:
            company_id = res[0]
            
    if company_id:
        # We want the LATEST period_end for EACH ratio name
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                WITH ranked_ratios AS (
                    SELECT name, value, period_end,
                           ROW_NUMBER() OVER (PARTITION BY name ORDER BY period_end DESC) as rn
                    FROM financial_ratios
                    WHERE company_id = %s
                )
                SELECT name, value, period_end
                FROM ranked_ratios
                WHERE rn = 1
            """, (company_id,))
            rows = cursor.fetchall()
            
            found_ratios = {}
            for row in rows:
                found_ratios[row['name']] = float(row['value']) if row['value'] is not None else None
                
            evidence_pack["financial_ratios"] = found_ratios
            
            # Find missing ratios (using our expected list, or maybe just anything not found)
            # The prompt doesn't specify an exact list, but I created EXPECTED_RATIOS.
            # I can just use it, or maybe wait and see if tests enforce something.
            missing = []
            for r in EXPECTED_RATIOS:
                if r not in found_ratios or found_ratios[r] is None:
                    missing.append(r)
            evidence_pack["missing_ratios"] = missing
            
    else:
        evidence_pack["missing_ratios"] = EXPECTED_RATIOS
        
    # 2. RAG Queries
    for query in RAG_QUERIES:
        # run hybrid search
        chunks = hybrid_search(
            conn=conn,
            query=query,
            filters={"ticker": ticker},
            top_k=3
        )
        
        evidence_pack["rag_chunks"][query] = []
        for c in chunks:
            evidence_pack["rag_chunks"][query].append({
                "text": c.text,
                "score": c.score,
                "citation": {
                    "source": c.citation.source_document,
                    "section": c.citation.section,
                    "chunk_id": c.citation.chunk_id
                }
            })
            
    return evidence_pack
