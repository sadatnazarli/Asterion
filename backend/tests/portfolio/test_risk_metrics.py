import pytest
from app.portfolio.risk_metrics import (
    calculate_portfolio_value,
    calculate_position_weights,
    calculate_sector_concentration,
    calculate_theme_concentration,
    calculate_single_name_concentration,
    calculate_speculative_exposure,
    calculate_core_etf_exposure,
    calculate_unrealized_pl_percentage
)

@pytest.fixture
def sample_positions():
    return [
        {
            "ticker": "AAPL",
            "quantity": 10.0,
            "average_cost": 140.0,
            "current_price": 150.0,
            "current_value": 1500.0,
            "asset_type": "Stock",
            "notes": "Core tech"
        },
        {
            "ticker": "MSFT",
            "quantity": 5.0,
            "average_cost": 200.0,
            "current_price": 250.0,
            "current_value": 1250.0,
            "asset_type": "Stock",
            "notes": "Growth"
        },
        {
            "ticker": "SPY",
            "quantity": 10.0,
            "average_cost": 400.0,
            "current_price": 450.0,
            "current_value": 4500.0,
            "asset_type": "ETF",
            "notes": "Core ETF"
        },
        {
            "ticker": "CRSP",
            "quantity": 100.0,
            "average_cost": 40.0,
            "current_price": 50.0,
            "current_value": 5000.0,
            "asset_type": "Stock",
            "notes": "Speculative biotech"
        }
    ]

def test_calculate_portfolio_value(sample_positions):
    # AAPL = 1500, MSFT = 1250, SPY = 4500, CRSP = 5000 -> Total = 12250.0
    assert calculate_portfolio_value(sample_positions) == 12250.0

def test_calculate_position_weights(sample_positions):
    weights = calculate_position_weights(sample_positions)
    assert weights["AAPL"] == 1500.0 / 12250.0
    assert weights["MSFT"] == 1250.0 / 12250.0
    assert weights["SPY"] == 4500.0 / 12250.0
    assert weights["CRSP"] == 5000.0 / 12250.0

def test_calculate_sector_concentration(sample_positions):
    conc = calculate_sector_concentration(sample_positions)
    assert conc["Stock"] == (1500.0 + 1250.0 + 5000.0) / 12250.0
    assert conc["ETF"] == 4500.0 / 12250.0

def test_calculate_theme_concentration(sample_positions):
    conc = calculate_theme_concentration(sample_positions)
    assert conc["Core tech"] == 1500.0 / 12250.0
    assert conc["Growth"] == 1250.0 / 12250.0
    assert conc["Core ETF"] == 4500.0 / 12250.0
    assert conc["Speculative biotech"] == 5000.0 / 12250.0

def test_calculate_single_name_concentration(sample_positions):
    conc = calculate_single_name_concentration(sample_positions)
    assert conc["AAPL"] == 1500.0 / 12250.0
    assert conc["SPY"] == 4500.0 / 12250.0
    assert conc["CRSP"] == 5000.0 / 12250.0

def test_calculate_speculative_exposure(sample_positions):
    assert calculate_speculative_exposure(sample_positions) == 5000.0 / 12250.0

def test_calculate_core_etf_exposure(sample_positions):
    assert calculate_core_etf_exposure(sample_positions) == 6000.0 / 12250.0 # "Core" is in AAPL and SPY

def test_calculate_unrealized_pl_percentage(sample_positions):
    pl_pct = calculate_unrealized_pl_percentage(sample_positions)
    # AAPL cost = 140*10 = 1400, current = 1500
    assert pl_pct["AAPL"] == (1500.0 - 1400.0) / 1400.0
    # MSFT cost = 200*5 = 1000, current = 1250
    assert pl_pct["MSFT"] == (1250.0 - 1000.0) / 1000.0
    # SPY cost = 400*10 = 4000, current = 4500
    assert pl_pct["SPY"] == (4500.0 - 4000.0) / 4000.0
    # CRSP cost = 40*100 = 4000, current = 5000
    assert pl_pct["CRSP"] == (5000.0 - 4000.0) / 4000.0
    
    total_cost = 1400.0 + 1000.0 + 4000.0 + 4000.0
    total_current = 12250.0
    assert pl_pct["TOTAL"] == (total_current - total_cost) / total_cost
