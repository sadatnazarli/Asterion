import re

# Common 10-K and 10-Q sections
# Regexes map standard section identifiers to their parsed content. We try to be case-insensitive
# and allow for variations in spacing or minor typos ("Item 1.", "ITEM 1", "Item  1A", etc.)

SECTIONS = [
    ("Item 1. Business", re.compile(r"^item\s+1\b\.?\s+business$", re.IGNORECASE)),
    ("Item 1A. Risk Factors", re.compile(r"^item\s+1a\b\.?\s+risk\s+factors$", re.IGNORECASE)),
    ("Item 1B. Unresolved Staff Comments", re.compile(r"^item\s+1b\b\.?\s+unresolved\s+staff\s+comments$", re.IGNORECASE)),
    ("Item 2. Properties", re.compile(r"^item\s+2\b\.?\s+properties$", re.IGNORECASE)),
    ("Item 3. Legal Proceedings", re.compile(r"^item\s+3\b\.?\s+legal\s+proceedings$", re.IGNORECASE)),
    ("Item 4. Mine Safety Disclosures", re.compile(r"^item\s+4\b\.?\s+mine\s+safety\s+disclosures$", re.IGNORECASE)),
    ("Item 5. Market for Registrant", re.compile(r"^item\s+5\b\.?\s+market\s+for\s+registrant", re.IGNORECASE)),
    ("Item 6. Selected Financial Data", re.compile(r"^item\s+6\b\.?\s+selected\s+financial\s+data$", re.IGNORECASE)),
    ("Item 7. Management's Discussion", re.compile(r"^item\s+7\b\.?\s+management(?:'|’)s\s+discussion\s+and\s+analysis", re.IGNORECASE)),
    ("Item 7A. Quantitative and Qualitative Disclosures", re.compile(r"^item\s+7a\b\.?\s+quantitative\s+and\s+qualitative\s+disclosures", re.IGNORECASE)),
    ("Item 8. Financial Statements", re.compile(r"^item\s+8\b\.?\s+financial\s+statements", re.IGNORECASE)),
    ("Item 9. Changes in and Disagreements", re.compile(r"^item\s+9\b\.?\s+changes\s+in\s+and\s+disagreements", re.IGNORECASE)),
    ("Item 9A. Controls and Procedures", re.compile(r"^item\s+9a\b\.?\s+controls\s+and\s+procedures$", re.IGNORECASE)),
    ("Item 9B. Other Information", re.compile(r"^item\s+9b\b\.?\s+other\s+information$", re.IGNORECASE)),
]

def extract_sections(text: str) -> list[tuple[str, str]]:
    """
    Attempt to parse SEC filing text into known sections.
    If unable to find any clear boundaries, returns the entire text under 'Full Document'.
    """
    lines = text.split('\n')
    extracted = []
    
    current_section = "Full Document"
    current_text_buffer = []
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            current_text_buffer.append(line)
            continue
            
        matched = False
        for section_name, pattern in SECTIONS:
            # Only match relatively short lines to avoid matching "Item 1" inside a paragraph
            if len(clean_line) < 150 and pattern.search(clean_line):
                # Save previous section if it had content
                if current_text_buffer:
                    joined_text = '\n'.join(current_text_buffer).strip()
                    if joined_text:
                        extracted.append((current_section, joined_text))
                
                current_section = section_name
                current_text_buffer = [line]
                matched = True
                break
                
        if not matched:
            current_text_buffer.append(line)
            
    if current_text_buffer:
        joined_text = '\n'.join(current_text_buffer).strip()
        if joined_text:
            extracted.append((current_section, joined_text))
            
    # If the only section is "Full Document", or if no sections matched properly, 
    # just return the whole text as "Full Document"
    if len(extracted) <= 1 and extracted and extracted[0][0] == "Full Document":
        return [("Full Document", text.strip())]
        
    # There could be some prefix text before the first section, which would be captured as "Full Document"
    # We will keep it.
    
    return extracted
