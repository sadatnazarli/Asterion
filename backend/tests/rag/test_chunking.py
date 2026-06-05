import pytest
from app.rag.chunking import chunk_sections, get_text_hash

def test_chunk_sections_basic():
    sections = [
        ("Section1", "A" * 2000),
        ("Section2", "B" * 500)
    ]
    metadata = {"accession_number": "0001", "filing_type": "10-K"}
    
    # 2000 chars, chunk size 1500, overlap 200. Step = 1300
    # chunk 1: 0 to 1500
    # chunk 2: 1300 to 2800 (but string is 2000, so 1300 to 2000, len 700)
    # Section2: 500 chars, chunk size 1500 -> 1 chunk
    
    chunks = chunk_sections(sections, metadata, chunk_size=1500, chunk_overlap=200)
    
    assert len(chunks) == 3
    
    assert chunks[0]["section_name"] == "Section1"
    assert len(chunks[0]["text"]) == 1500
    assert chunks[0]["accession_number"] == "0001"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["text_hash"] == get_text_hash(chunks[0]["text"])
    
    assert chunks[1]["section_name"] == "Section1"
    assert len(chunks[1]["text"]) == 700
    assert chunks[1]["chunk_index"] == 1
    
    assert chunks[2]["section_name"] == "Section2"
    assert len(chunks[2]["text"]) == 500
    assert chunks[2]["chunk_index"] == 2

def test_chunk_sections_empty():
    sections = [("Empty", "")]
    metadata = {}
    chunks = chunk_sections(sections, metadata)
    assert chunks == []

def test_chunk_sections_invalid_args():
    with pytest.raises(ValueError):
        chunk_sections([("A", "text")], {}, chunk_size=100, chunk_overlap=150)
