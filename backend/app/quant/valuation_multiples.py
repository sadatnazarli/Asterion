"""Valuation Multiples and Metrics.

Pure python functions to calculate fundamental valuation metrics.
All functions tolerate `None` or <= 0 inputs gracefully, returning `None` or 
handling edge cases.
"""
from __future__ import annotations


def calculate_market_cap(shares_outstanding: float | None, price: float | None) -> float | None:
    """Calculate Market Capitalization."""
    if shares_outstanding is None or price is None:
        return None
    if shares_outstanding <= 0 or price < 0:
        return None
    return shares_outstanding * price


def calculate_enterprise_value(
    market_cap: float | None, 
    total_debt: float | None, 
    cash_and_equivalents: float | None
) -> float | None:
    """Calculate Enterprise Value (EV).
    
    EV = Market Cap + Total Debt - Cash and Equivalents
    """
    if market_cap is None:
        return None
        
    debt = total_debt if total_debt is not None else 0.0
    cash = cash_and_equivalents if cash_and_equivalents is not None else 0.0
    
    return market_cap + debt - cash


def calculate_ev_to_sales(enterprise_value: float | None, revenue: float | None) -> float | None:
    """Calculate EV/Sales multiple."""
    if enterprise_value is None or revenue is None:
        return None
    if revenue <= 0:
        return None
    return enterprise_value / revenue


def calculate_p_to_fcf(market_cap: float | None, free_cash_flow: float | None) -> float | None:
    """Calculate Price to Free Cash Flow (P/FCF) multiple."""
    if market_cap is None or free_cash_flow is None:
        return None
    if free_cash_flow <= 0:
        return None  # P/FCF isn't meaningful with negative FCF
    return market_cap / free_cash_flow


def calculate_fcf_yield(free_cash_flow: float | None, market_cap: float | None) -> float | None:
    """Calculate Free Cash Flow Yield."""
    if free_cash_flow is None or market_cap is None:
        return None
    if market_cap <= 0:
        return None
    return free_cash_flow / market_cap
