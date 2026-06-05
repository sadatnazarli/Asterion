from bs4 import BeautifulSoup
from app.rag.sec_filing_sections import extract_sections

def parse_filing_document(raw_bytes: bytes, extension: str = 'html') -> list[tuple[str, str]]:
    """
    Parse raw SEC filing document (HTML or TXT) into sections.
    
    Args:
        raw_bytes: The raw bytes of the SEC filing document.
        extension: The file extension (e.g. 'html', 'htm', 'txt').
        
    Returns:
        A list of tuples containing (section_name, section_text).
    """
    ext = extension.lower()
    
    if ext in ('html', 'htm'):
        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(raw_bytes, 'html.parser')
        
        # We want to extract text while keeping paragraphs separated nicely.
        # Get text with '\n' as separator for blocks
        text = soup.get_text(separator='\n', strip=True)
    else:
        # For .txt or other formats, decode directly
        # Sometimes sec uses latin-1 or windows-1252, but utf-8 usually works with replace
        text = raw_bytes.decode('utf-8', errors='replace')
        
    return extract_sections(text)
