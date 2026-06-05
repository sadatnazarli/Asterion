import pytest
from app.scoring import advanced_scores

def test_operating_leverage_convexity_full_data():
    inputs = {
        "gross_margin": 0.80,
        "revenue_growth_yoy": 0.20
    }
    result = advanced_scores.calculate_operating_leverage_convexity(inputs)
    assert result["confidence"] == 1.0
    assert len(result["missing_inputs"]) == 0
    assert result["score"] == 50 + (0.80 * 100 * 0.20) # 50 + 16 = 66
    
def test_operating_leverage_convexity_missing_data():
    inputs = {
        "gross_margin": 0.80
        # revenue_growth_yoy is missing
    }
    result = advanced_scores.calculate_operating_leverage_convexity(inputs)
    assert result["confidence"] == 0.5
    assert "revenue_growth_yoy" in result["missing_inputs"]
    assert "gross_margin" in result["inputs_used"]
    # With rev_growth default 0, score is 50
    assert result["score"] == 50.0
    
def test_operating_leverage_convexity_all_missing():
    result = advanced_scores.calculate_operating_leverage_convexity({})
    assert result["confidence"] == 0.0
    assert len(result["missing_inputs"]) == 2
    assert result["score"] == 50.0

def test_reflexivity_risk():
    inputs = {
        "current_ratio": 1.0,
        "debt_to_equity": 2.0
    }
    result = advanced_scores.calculate_reflexivity_risk(inputs)
    assert result["confidence"] == 1.0
    # risk = (2.0 * 20) + ((2.0 - 1.0)*20) = 40 + 20 = 60
    assert result["score"] == 60.0

def test_misunderstood_change():
    inputs = {
        "sentiment_shift": 0.2, # bad sentiment
        "capex_growth": 0.3    # high capex
    }
    result = advanced_scores.calculate_misunderstood_change(inputs)
    # score = 50 + 30 - 10 = 70
    assert result["score"] == 70.0
    assert result["confidence"] == 1.0

def test_perception_shift():
    inputs = {"analyst_revisions": 0.8, "earnings_surprise": 0.1}
    result = advanced_scores.calculate_perception_shift(inputs)
    # score = 50 + 40 + 10 = 100
    assert result["score"] == 100.0

def test_narrative_entropy():
    inputs = {"management_tone_variance": 0.8, "topic_dispersion": 0.6}
    result = advanced_scores.calculate_narrative_entropy(inputs)
    # 40 + 30 = 70
    assert result["score"] == 70.0


