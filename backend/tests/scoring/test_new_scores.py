import pytest
from app.scoring.expectations_gap import calculate_expectations_gap
from app.scoring.thesis_fragility import calculate_thesis_fragility

def test_expectations_gap():
    inputs = {"implied_growth": 0.25, "historical_growth_ttm": 0.15}
    result = calculate_expectations_gap(inputs)
    assert result["confidence"] == 1.0
    # gap = 0.25 - 0.15 = 0.10
    # score = 50 + (0.10 * 250) = 50 + 25 = 75
    assert result["score"] == 75.0

def test_thesis_fragility_new():
    inputs = {"dcf_sensitivity_impact": 0.8}
    result = calculate_thesis_fragility(inputs)
    assert result["confidence"] == 1.0
    # score = 0.8 * 100 = 80
    assert result["score"] == 80.0
