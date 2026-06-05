import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from app.analysis.company_context import build_evidence_pack, EXPECTED_RATIOS
from app.rag.evidence_pack import EvidencePack
from app.rag.citations import Citation

def test_build_evidence_pack_no_company():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    # Simulate ticker not found
    cursor.fetchone.return_value = None
    
    with patch('app.analysis.company_context.hybrid_search', return_value=[]):
        pack = build_evidence_pack(conn, "UNKNOWN")
        
    assert pack["ticker"] == "UNKNOWN"
    assert pack["financial_ratios"] == {}
    assert pack["missing_ratios"] == EXPECTED_RATIOS
    assert "business model" in pack["rag_chunks"]

def test_build_evidence_pack_success():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    
    # 1st call: get company_id
    # 2nd call: get financial ratios
    def fetchone_side_effect(*args, **kwargs):
        return (1,)
        
    def fetchall_side_effect(*args, **kwargs):
        return [
            {"name": "gross_margin", "value": 45.5, "period_end": "2023-12-31"},
            {"name": "net_margin", "value": 10.2, "period_end": "2023-12-31"}
        ]
        
    cursor.fetchone.side_effect = fetchone_side_effect
    cursor.fetchall.side_effect = fetchall_side_effect
    
    mock_ep = EvidencePack(
        text="Strong business model.",
        citation=Citation(
            source_document="AAPL-10-K",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            section="Business",
            accession_number="0001",
            chunk_id="1"
        ),
        score=0.95
    )
    
    with patch('app.analysis.company_context.hybrid_search', return_value=[mock_ep]):
        pack = build_evidence_pack(conn, "AAPL")
        
    assert pack["ticker"] == "AAPL"
    assert pack["financial_ratios"]["gross_margin"] == 45.5
    assert pack["financial_ratios"]["net_margin"] == 10.2
    assert "gross_margin" not in pack["missing_ratios"]
    assert "operating_margin" in pack["missing_ratios"]
    
    assert len(pack["rag_chunks"]["business model"]) == 1
    assert pack["rag_chunks"]["business model"][0]["text"] == "Strong business model."
