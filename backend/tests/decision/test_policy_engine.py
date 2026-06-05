import pytest
from app.decision.schemas import PolicyClassification
from app.decision.policy_engine import evaluate_policy

def test_no_financial_advice_in_classifications():
    """Ensure our allowed classifications never use buy/sell/price targets."""
    forbidden_words = ["buy", "sell", "hold", "price target", "overweight", "underweight"]
    
    for classification in PolicyClassification:
        for word in forbidden_words:
            assert word not in classification.value.lower(), f"Forbidden word '{word}' found in classification {classification.value}"

def test_evaluate_policy_wait_for_valuation():
    ratios = {"debt_to_equity": 1.0, "roa": 0.05, "roe": 0.1}
    advanced_scores = {"Operating Leverage Convexity Score": {"score": 50}}
    missing_data = ["pe_ratio"]
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.wait_for_valuation_data
    assert "cannot determine attractiveness" in output.reason

def test_evaluate_policy_quality_compounder():
    ratios = {"pe_ratio": 20, "debt_to_equity": 0.5, "roa": 0.1, "roe": 0.2, "gross_margin": 0.8, "fcf_margin": 0.2}
    advanced_scores = {"Operating Leverage Convexity Score": {"score": 80}}
    missing_data = []
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.quality_compounder_candidate
    assert output.confidence == 0.85

def test_evaluate_policy_insufficient_data():
    ratios = {}
    advanced_scores = {}
    missing_data = ["pe_ratio", "debt_to_equity", "roa", "roe", "gross_margin", "fcf_margin"]
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.insufficient_data
    assert "Too many missing data points" in output.reason

def test_evaluate_policy_avoid_due_to_red_flags():
    ratios = {"pe_ratio": 10, "debt_to_equity": 3.0, "roa": -0.05, "roe": -0.1}
    advanced_scores = {"Reflexivity Risk Score": {"score": 90}}
    missing_data = []
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.avoid_due_to_red_flags
    assert len(output.red_flags) >= 2

def test_evaluate_policy_no_financial_advice_in_reason():
    ratios = {"pe_ratio": 20, "debt_to_equity": 0.5, "roa": 0.1, "roe": 0.2, "gross_margin": 0.8, "fcf_margin": 0.2}
    advanced_scores = {"Operating Leverage Convexity Score": {"score": 80}}
    missing_data = []
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    
    forbidden_words = ["buy", "sell", "hold", "target price"]
    for word in forbidden_words:
        assert word not in output.reason.lower()

def test_evaluate_policy_valuation_risk_watchlist():
    ratios = {"pe_ratio": 50, "debt_to_equity": 0.5, "roa": 0.1, "roe": 0.2, "gross_margin": 0.8, "fcf_margin": 0.2}
    advanced_scores = {
        "operating_leverage_convexity": {"score": 80},
        "expectations_gap": {"score": 85}
    }
    missing_data = []
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.valuation_risk_watchlist

def test_evaluate_policy_wait_for_better_price():
    ratios = {"pe_ratio": 30, "debt_to_equity": 0.5, "roa": 0.1, "roe": 0.2, "gross_margin": 0.8, "fcf_margin": 0.2}
    advanced_scores = {
        "operating_leverage_convexity": {"score": 80},
        "expectations_gap": {"score": 60}
    }
    missing_data = []
    
    output = evaluate_policy(ratios, advanced_scores, missing_data)
    assert output.classification == PolicyClassification.wait_for_better_price
