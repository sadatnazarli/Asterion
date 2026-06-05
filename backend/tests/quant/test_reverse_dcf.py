import pytest
from app.quant.reverse_dcf import implied_growth_rate, reverse_dcf_sensitivity

def test_implied_growth_rate():
    # Example: If FCF is 100, EV is 2000, r = 0.10, term_g = 0.025, horizon=10
    g = implied_growth_rate(2000, 100, 0.10, 0.025, 10)
    assert g is not None
    assert 0.0 <= g <= 0.10  # Plausible bounds
    
    # Test negative FCF
    assert implied_growth_rate(2000, -10) is None
    
    # Test zero EV
    assert implied_growth_rate(0, 100) is None
    
    # Test r <= term_g
    assert implied_growth_rate(2000, 100, 0.02, 0.03) is None

def test_reverse_dcf_sensitivity():
    res = reverse_dcf_sensitivity(2000, 100)
    
    assert "discount_rates" in res
    assert "terminal_growths" in res
    assert "implied_growth_matrix" in res
    
    dr = res["discount_rates"]
    tg = res["terminal_growths"]
    mat = res["implied_growth_matrix"]
    
    assert len(mat) == len(dr)
    assert len(mat[0]) == len(tg)
    
    # Values in matrix should be floats or None
    assert isinstance(mat[0][0], float) or mat[0][0] is None
