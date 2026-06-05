import pytest
from app.scoring.advanced_registry import AdvancedScoreRegistry

def test_registry_has_10_scores():
    registry = AdvancedScoreRegistry()
    assert len(registry.scores) == 10

def test_get_implementable_scores_p0_only():
    registry = AdvancedScoreRegistry()
    # Provide one input for a P0 and one for a P1
    available = ["gross_margin", "implied_growth"]
    scores = registry.get_implementable_scores(available, max_priority="P0")
    
    # Should only return operating_leverage_convexity because implied_growth is P1
    assert len(scores) == 1
    assert scores[0].key == "operating_leverage_convexity"

def test_get_implementable_scores_p1_allowed():
    registry = AdvancedScoreRegistry()
    available = ["gross_margin", "implied_growth"]
    scores = registry.get_implementable_scores(available, max_priority="P1")
    
    keys = [s.key for s in scores]
    assert "operating_leverage_convexity" in keys
    assert "expectations_gap" in keys
    assert len(keys) == 2

def test_get_implementable_scores_missing_all_data():
    registry = AdvancedScoreRegistry()
    available = []
    scores = registry.get_implementable_scores(available, max_priority="P3")
    assert len(scores) == 0
