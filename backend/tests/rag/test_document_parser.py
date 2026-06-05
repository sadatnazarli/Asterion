import pytest
from app.rag.document_parser import parse_filing_document
from app.rag.sec_filing_sections import extract_sections

def test_extract_sections_full_document():
    text = "Just some regular text without any item headers.\nIt should be full document."
    sections = extract_sections(text)
    assert len(sections) == 1
    assert sections[0][0] == "Full Document"
    assert sections[0][1] == text

def test_extract_sections_with_items():
    text = """
Some prefix text here.
Item 1. Business
This is the business section.
It spans multiple lines.
Item 1A. Risk Factors
These are the risk factors.
    """
    sections = extract_sections(text)
    
    # We expect 3 sections: Full Document (prefix), Item 1. Business, Item 1A. Risk Factors
    assert len(sections) == 3
    
    assert sections[0][0] == "Full Document"
    assert "Some prefix text here." in sections[0][1]
    
    assert sections[1][0] == "Item 1. Business"
    assert "Item 1. Business" in sections[1][1]
    assert "This is the business section." in sections[1][1]
    
    assert sections[2][0] == "Item 1A. Risk Factors"
    assert "Item 1A. Risk Factors" in sections[2][1]
    assert "These are the risk factors." in sections[2][1]

def test_parse_filing_document_txt():
    raw_bytes = b"Item 1. Business\nThis is business text."
    sections = parse_filing_document(raw_bytes, "txt")
    
    assert len(sections) == 1
    assert sections[0][0] == "Item 1. Business"
    assert "This is business text." in sections[0][1]

def test_parse_filing_document_html():
    html_content = b"""
    <html>
        <body>
            <p>Some header info</p>
            <div><b>Item 1. Business</b></div>
            <p>Business text goes here.</p>
        </body>
    </html>
    """
    sections = parse_filing_document(html_content, "html")
    
    assert len(sections) == 2
    assert sections[0][0] == "Full Document"
    assert "Some header info" in sections[0][1]
    
    assert sections[1][0] == "Item 1. Business"
    assert "Business text goes here." in sections[1][1]
