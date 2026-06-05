import re

def repair_json(text: str) -> str:
    """
    Attempt to repair common JSON formatting errors from LLMs.
    """
    # Strip whitespace
    text = text.strip()
    
    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    # Fix trailing commas
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    return text
