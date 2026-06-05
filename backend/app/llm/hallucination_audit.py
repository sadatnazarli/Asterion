import re
from typing import Dict, Any, List, Set

# Match numbers, optional decimals, optional modifiers (K, M, B, %).
# For word characters (KMB), we need \b. For %, we don't.
NUMBER_PATTERN = re.compile(r'\b\d+(?:\.\d+)?(?:[KMB]\b|%)?')

def extract_numbers(text: str) -> Set[str]:
    if not isinstance(text, str):
        text = str(text)
    return set(match.group(0).upper() for match in NUMBER_PATTERN.finditer(text))

def extract_numbers_from_pack(pack: Any) -> Set[str]:
    numbers = set()
    if isinstance(pack, dict):
        for k, v in pack.items():
            numbers.update(extract_numbers_from_pack(v))
    elif isinstance(pack, list):
        for item in pack:
            numbers.update(extract_numbers_from_pack(item))
    elif isinstance(pack, (str, int, float)):
        numbers.update(extract_numbers(str(pack)))
    return numbers

def audit_hallucinations(llm_output: str, evidence_pack: dict) -> Dict[str, Any]:
    llm_numbers = extract_numbers(llm_output)
    pack_numbers = extract_numbers_from_pack(evidence_pack)
    
    suspicious = []
    for num in llm_numbers:
        if num not in pack_numbers:
            suspicious.append(num)
            
    return {
        "pass": len(suspicious) == 0,
        "suspicious_numbers": sorted(suspicious),
        "source_checked": True
    }
