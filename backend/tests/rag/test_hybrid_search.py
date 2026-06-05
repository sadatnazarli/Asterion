import pytest
from datetime import date
from unittest.mock import MagicMock
from app.rag.hybrid_search import hybrid_search, SECTION_WEIGHTS
from app.rag.citations import Citation
from app.rag.evidence_pack import EvidencePack

def test_hybrid_search_bm25_only():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    # Mocking that pgvector column check fails/returns empty
    cursor.fetchone.return_value = None
    
    # Mock search results
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "ticker": "PLTR",
            "document_type": "10-K",
            "filing_type": "10-K",
            "filing_date": date(2023, 2, 28),
            "section_name": "Business",
            "accession_number": "0001",
            "text": "Palantir builds software.",
            "base_score": 1.0
        },
        {
            "id": 2,
            "ticker": "PLTR",
            "document_type": "10-K",
            "filing_type": "10-K",
            "filing_date": date(2023, 2, 28),
            "section_name": "Risk Factors",
            "accession_number": "0001",
            "text": "Our software has risks.",
            "base_score": 0.8
        }
    ]
    
    results = hybrid_search(conn, "software", top_k=2)
    
    assert len(results) == 2
    assert isinstance(results[0], EvidencePack)
    
    # Check section weight application
    # Result 1: Business (weight 1.2) -> 1.0 * 1.2 = 1.2
    # Result 2: Risk Factors (weight 1.5) -> 0.8 * 1.5 = 1.2
    # So both get 1.2 score
    assert results[0].score == pytest.approx(1.2)
    assert results[1].score == pytest.approx(1.2)
    
    # Verify the SQL structure
    execute_calls = cursor.execute.call_args_list
    assert len(execute_calls) >= 1

def test_hybrid_search_with_vector():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    def fetchone_side_effect():
        # First call is to check if embedding column exists
        yield {"column_name": "embedding"}
        
    cursor.fetchone.side_effect = fetchone_side_effect()
    
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "ticker": "PLTR",
            "document_type": "10-K",
            "filing_type": "10-K",
            "filing_date": date(2023, 2, 28),
            "section_name": "Management's Discussion and Analysis",
            "accession_number": "0001",
            "text": "Financial results were good.",
            "base_score": 2.0
        }
    ]
    
    results = hybrid_search(conn, "financial", query_embedding=[0.1, 0.2, 0.3], top_k=1)
    
    assert len(results) == 1
    assert results[0].citation.section == "Management's Discussion and Analysis"
    assert results[0].score == 2.0 * SECTION_WEIGHTS["Management's Discussion and Analysis"]
