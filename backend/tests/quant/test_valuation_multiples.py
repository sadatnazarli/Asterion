import pytest
from app.quant.valuation_multiples import (
    calculate_market_cap,
    calculate_enterprise_value,
    calculate_ev_to_sales,
    calculate_p_to_fcf,
    calculate_fcf_yield,
)

def test_calculate_market_cap():
    assert calculate_market_cap(100, 50) == 5000.0
    assert calculate_market_cap(None, 50) is None
    assert calculate_market_cap(100, None) is None
    assert calculate_market_cap(-10, 50) is None
    assert calculate_market_cap(100, -5) is None

def test_calculate_enterprise_value():
    assert calculate_enterprise_value(5000, 1000, 500) == 5500.0
    assert calculate_enterprise_value(None, 1000, 500) is None
    # Defaulting None debt or cash to 0
    assert calculate_enterprise_value(5000, None, 500) == 4500.0
    assert calculate_enterprise_value(5000, 1000, None) == 6000.0
    assert calculate_enterprise_value(5000, None, None) == 5000.0

def test_calculate_ev_to_sales():
    assert calculate_ev_to_sales(5000, 1000) == 5.0
    assert calculate_ev_to_sales(None, 1000) is None
    assert calculate_ev_to_sales(5000, None) is None
    assert calculate_ev_to_sales(5000, 0) is None
    assert calculate_ev_to_sales(5000, -100) is None

def test_calculate_p_to_fcf():
    assert calculate_p_to_fcf(5000, 250) == 20.0
    assert calculate_p_to_fcf(None, 250) is None
    assert calculate_p_to_fcf(5000, None) is None
    assert calculate_p_to_fcf(5000, 0) is None
    assert calculate_p_to_fcf(5000, -50) is None

def test_calculate_fcf_yield():
    assert calculate_fcf_yield(250, 5000) == 0.05
    assert calculate_fcf_yield(None, 5000) is None
    assert calculate_fcf_yield(250, None) is None
    assert calculate_fcf_yield(250, 0) is None
    assert calculate_fcf_yield(250, -100) is None
