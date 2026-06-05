import pytest
from app.llm.hallucination_audit import extract_numbers, extract_numbers_from_pack, audit_hallucinations

def test_extract_numbers():
    assert extract_numbers("The company made 10M and 20.5% growth.") == {"10M", "20.5%"}
    assert extract_numbers("No numbers here!") == set()
    assert extract_numbers("10 20 30") == {"10", "20", "30"}
    assert extract_numbers("10B, 5K") == {"10B", "5K"}

def test_extract_numbers_from_pack():
    pack = {
        "ratios": {
            "margin": 15.5,
            "growth": "20%"
        },
        "texts": [
            "Revenue was 100M.",
            "Net income 50K."
        ],
        "missing": []
    }
    extracted = extract_numbers_from_pack(pack)
    assert extracted == {"15.5", "20%", "100M", "50K"}

def test_audit_hallucinations_pass():
    pack = {"text": "Revenue was 100M and growth was 20%."}
    output = "The revenue hit 100M, showing a 20% growth."
    res = audit_hallucinations(output, pack)
    assert res["pass"] is True
    assert res["suspicious_numbers"] == []
    assert res["source_checked"] is True

def test_audit_hallucinations_fail():
    pack = {"text": "Revenue was 100M and growth was 20%."}
    output = "The revenue hit 200M, showing a 25% growth."
    res = audit_hallucinations(output, pack)
    assert res["pass"] is False
    assert set(res["suspicious_numbers"]) == {"200M", "25%"}
