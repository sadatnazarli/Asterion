import hashlib
from typing import Any, Dict, List, Tuple

def get_text_hash(text: str) -> str:
    """Generate SHA-256 hash for a given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_sections(
    sections: List[Tuple[str, str]], 
    metadata: Dict[str, Any],
    chunk_size: int = 1500,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Splits sections of text into chunks using a sliding window without crossing sections.
    
    Args:
        sections: List of tuples (section_name, text).
        metadata: Dictionary containing metadata (e.g., accession_number, filing_type).
        chunk_size: The number of characters in each chunk.
        chunk_overlap: The number of overlapping characters between chunks.
        
    Returns:
        List of dictionaries representing chunks with text, hash, indices, and metadata.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    
    step = chunk_size - chunk_overlap
    if step <= 0:
        raise ValueError("chunk_overlap must be less than chunk_size")

    chunks = []
    chunk_index = 0

    for section_name, text in sections:
        if not text:
            continue
            
        for i in range(0, len(text), step):
            # Extract the chunk from the current section text
            chunk_text = text[i:i + chunk_size]
            
            chunk_dict = {
                "section_name": section_name,
                "text": chunk_text,
                "text_hash": get_text_hash(chunk_text),
                "chunk_index": chunk_index,
            }
            # Add all metadata keys
            chunk_dict.update(metadata)
            chunks.append(chunk_dict)
            
            chunk_index += 1
            
            # If the current chunk reaches the end of the text, break
            if i + chunk_size >= len(text):
                break

    return chunks
