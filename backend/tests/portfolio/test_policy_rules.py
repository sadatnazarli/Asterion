import pytest
from app.portfolio.policy_rules import check_portfolio_policies

def test_check_portfolio_policies():
    positions = [
        {
            "ticker": "TSLA",
            "quantity": 1000,
            "average_cost": 100.0,
            "current_price": 200.0, # Value = 200,000 (20% single stock -> >15%)
            "asset_type": "Auto",
            "notes": "EV",
            "is_speculative": False,
            "is_core_etf": False
        },
        {
            "ticker": "SPY",
            "quantity": 1000,
            "average_cost": 400.0,
            "current_price": 400.0, # Value = 400,000 (40% Core ETF -> >30%, passes)
            "asset_type": "ETF",
            "notes": "Core",
            "is_speculative": False,
            "is_core_etf": True
        },
        {
            "ticker": "ARKK",
            "quantity": 3000,
            "average_cost": 50.0,
            "current_price": 100.0, # Value = 300,000 (30% Speculative -> >10%, 30% theme -> >25%)
            "asset_type": "Tech",
            "notes": "Disruptive speculative",
            "is_speculative": True,
            "is_core_etf": False
        },
        {
            "ticker": "AAPL",
            "quantity": 500,
            "average_cost": 100.0,
            "current_price": 200.0, # Value = 100,000 (10% single stock)
            "asset_type": "Tech",
            "notes": "Disruptive",
            "is_speculative": False,
            "is_core_etf": False
        }
    ]
    # Total Value = 200k + 400k + 300k + 100k = 1,000,000
    
    warnings = check_portfolio_policies(positions)
    
    assert any("TSLA" in w and "single stock concentration" in w.lower() for w in warnings), "Expected single stock warning for TSLA"
    assert not any("AAPL" in w and "single stock concentration" in w.lower() for w in warnings), "Did not expect single stock warning for AAPL"
    assert any("Disruptive" in w and "theme concentration" in w.lower() for w in warnings), "Expected theme warning for Disruptive (300k + 100k = 40%)"
    assert any("speculative exposure" in w.lower() for w in warnings), "Expected speculative exposure warning"

def test_check_portfolio_policies_core_etf_low():
    positions = [
        {
            "ticker": "AAPL",
            "quantity": 100,
            "cost_basis": 150.0,
            "current_price": 150.0, # Value = 15,000 (88%)
            "sector": "Technology",
            "theme": "AI",
            "is_speculative": False,
            "is_core_etf": False
        },
        {
            "ticker": "SPY",
            "quantity": 5,
            "cost_basis": 400.0,
            "current_price": 400.0, # Value = 2,000 (11%)
            "sector": "ETF",
            "theme": "Core",
            "is_speculative": False,
            "is_core_etf": True
        }
    ]
    # Total value = 17,000
    # Core ETF = 11.7% < 30%
    
    warnings = check_portfolio_policies(positions)
    assert any("core etf exposure" in w.lower() and "below" in w.lower() for w in warnings), "Expected low core ETF warning"
