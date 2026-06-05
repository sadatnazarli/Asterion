"""Sanity tests for every deterministic quant formula.

Known-value cases, division-by-zero, missing-data, negative values, and
confidence degradation. These pin the math so a refactor can't silently change
a number. Pure functions only — no DB, no network.
"""
from __future__ import annotations

import math

import pytest

from app.quant.fundamentals import (
    current_ratio,
    debt_to_equity,
    free_cash_flow_margin,
    gross_margin,
    net_margin,
    operating_margin,
    return_on_assets,
    return_on_equity,
    revenue_growth,
    sbc_to_revenue,
    shares_outstanding_change,
)
from app.quant.forensic import (
    accruals_ratio,
    altman_z_score,
    piotroski_f_score,
    quality_of_earnings,
)
from app.quant.reverse_dcf import implied_growth_rate
from app.quant.valuation import enterprise_value, fcf_yield, price_to_earnings


# ── Fundamentals: known values ────────────────────────────────────────────

def test_gross_margin_known_value():
    r = gross_margin(40.0, 100.0)
    assert r.value == pytest.approx(0.40)
    assert r.confidence == 1.0
    assert r.missing_flags == []


def test_revenue_growth_known_value():
    r = revenue_growth(120.0, 100.0)
    assert r.value == pytest.approx(0.20)


def test_revenue_growth_negative_prior_uses_abs_denominator():
    # prior is negative — formula divides by abs(prior)
    r = revenue_growth(-50.0, -100.0)
    assert r.value == pytest.approx((-50.0 - -100.0) / 100.0)  # +0.5


def test_net_margin_negative_income_allowed():
    r = net_margin(-25.0, 100.0)
    assert r.value == pytest.approx(-0.25)  # negative margin is valid


def test_operating_margin_known():
    assert operating_margin(30.0, 100.0).value == pytest.approx(0.30)


def test_fcf_margin_normalises_negative_capex():
    # capex reported negative; abs() applied before subtraction
    r = free_cash_flow_margin(operating_cash_flow=50.0, capex=-10.0, revenue=100.0)
    assert r.value == pytest.approx((50.0 - 10.0) / 100.0)  # 0.40


def test_roe_and_roa_known():
    assert return_on_equity(20.0, 200.0).value == pytest.approx(0.10)
    assert return_on_assets(20.0, 400.0).value == pytest.approx(0.05)


def test_current_ratio_and_dte_known():
    assert current_ratio(150.0, 100.0).value == pytest.approx(1.5)
    assert debt_to_equity(80.0, 160.0).value == pytest.approx(0.5)


# ── Division by zero ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "fn,args",
    [
        (gross_margin, (40.0, 0.0)),
        (operating_margin, (40.0, 0.0)),
        (net_margin, (40.0, 0.0)),
        (return_on_equity, (40.0, 0.0)),
        (return_on_assets, (40.0, 0.0)),
        (current_ratio, (40.0, 0.0)),
        (debt_to_equity, (40.0, 0.0)),
        (sbc_to_revenue, (40.0, 0.0)),
        (revenue_growth, (40.0, 0.0)),
        (shares_outstanding_change, (40.0, 0.0)),
    ],
)
def test_zero_denominator_returns_none_with_flag(fn, args):
    r = fn(*args)
    assert r.value is None
    assert "zero_denominator" in r.missing_flags


# ── Missing data ───────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "fn,args",
    [
        (gross_margin, (None, 100.0)),
        (operating_margin, (50.0, None)),
        (net_margin, (None, None)),
        (return_on_equity, (None, 200.0)),
        (current_ratio, (None, 100.0)),
        (debt_to_equity, (80.0, None)),
    ],
)
def test_missing_inputs_zero_confidence(fn, args):
    r = fn(*args)
    assert r.value is None
    assert r.confidence == 0.0
    assert r.missing_flags  # at least one flag


# ── Valuation ──────────────────────────────────────────────────────────────

def test_enterprise_value_known():
    r = enterprise_value(market_cap=1000.0, total_debt=200.0, cash_and_equivalents=50.0)
    assert r.value == pytest.approx(1150.0)


def test_enterprise_value_treats_missing_debt_cash_as_zero_but_lowers_confidence():
    r = enterprise_value(market_cap=1000.0, total_debt=None, cash_and_equivalents=None)
    assert r.value == pytest.approx(1000.0)
    assert r.confidence < 1.0
    assert "total_debt" in r.missing_flags


def test_enterprise_value_requires_market_cap():
    r = enterprise_value(market_cap=None, total_debt=10.0, cash_and_equivalents=5.0)
    assert r.value is None
    assert r.confidence == 0.0


def test_pe_negative_earnings_returns_value_but_flag_free():
    # negative net income → negative PE is a valid (if meaningless) ratio
    r = price_to_earnings(market_cap=1000.0, net_income=-50.0)
    assert r.value == pytest.approx(-20.0)


def test_fcf_yield_zero_market_cap_flags_division():
    r = fcf_yield(free_cash_flow=50.0, market_cap=0.0)
    assert r.value is None
    assert "division_by_zero" in r.missing_flags


# ── Forensic ───────────────────────────────────────────────────────────────

def test_altman_z_requires_total_assets():
    r = altman_z_score(total_assets=None, market_cap=100.0)
    assert r.value is None
    assert "total_assets" in r.missing_flags


def test_altman_z_partial_inputs_degrade_confidence():
    # all five components present → confidence 1.0
    full = altman_z_score(
        working_capital=10.0, retained_earnings=20.0, ebit=15.0,
        market_cap=300.0, total_liabilities=100.0, revenue=200.0, total_assets=400.0,
    )
    assert full.confidence == pytest.approx(1.0)
    # drop two components → confidence 3/5
    partial = altman_z_score(
        working_capital=None, retained_earnings=None, ebit=15.0,
        market_cap=300.0, total_liabilities=100.0, revenue=200.0, total_assets=400.0,
    )
    assert partial.confidence == pytest.approx(3 / 5)
    assert partial.value is not None  # still computes with available terms


def test_piotroski_perfect_company_scores_high():
    r = piotroski_f_score(
        net_income=100.0, operating_cash_flow=150.0,
        roa_current=0.12, roa_prior=0.10,
        long_term_debt_current=50.0, long_term_debt_prior=80.0,
        current_ratio_current=2.0, current_ratio_prior=1.5,
        shares_current=100.0, shares_prior=100.0,
        gross_margin_current=0.45, gross_margin_prior=0.40,
        asset_turnover_current=0.9, asset_turnover_prior=0.8,
    )
    assert r.value == 9
    assert r.confidence == pytest.approx(1.0)


def test_piotroski_missing_period_lowers_confidence():
    r = piotroski_f_score(net_income=100.0, operating_cash_flow=150.0)
    # only F1, F2, F4 scoreable → 3/9 confidence (stored rounded to 4dp)
    assert r.confidence == pytest.approx(3 / 9, abs=1e-3)
    assert "F3" in r.missing_flags


def test_accruals_ratio_quality_signal_sign():
    # OCF > NI → negative accruals (good quality)
    r = accruals_ratio(net_income=80.0, operating_cash_flow=120.0, total_assets=1000.0)
    assert r.value == pytest.approx((80.0 - 120.0) / 1000.0)
    assert r.value < 0


def test_quality_of_earnings_zero_income_returns_none():
    r = quality_of_earnings(operating_cash_flow=100.0, net_income=0.0)
    assert r.value is None


# ── Reverse DCF ────────────────────────────────────────────────────────────

def test_reverse_dcf_rejects_nonpositive_fcf():
    assert implied_growth_rate(enterprise_value=1000.0, fcf=0.0) is None
    assert implied_growth_rate(enterprise_value=1000.0, fcf=-10.0) is None


def test_reverse_dcf_rejects_nonpositive_ev():
    assert implied_growth_rate(enterprise_value=0.0, fcf=10.0) is None


def test_reverse_dcf_rejects_discount_le_terminal():
    # discount_rate must exceed terminal_growth for Gordon model
    assert implied_growth_rate(1000.0, 10.0, discount_rate=0.02, terminal_growth=0.025) is None


def test_reverse_dcf_solves_plausible_growth():
    # A company priced richly vs its FCF should imply positive growth.
    g = implied_growth_rate(enterprise_value=2000.0, fcf=50.0, discount_rate=0.10)
    assert g is not None
    assert -0.99 < g < 10.0
    # sanity: higher EV for same FCF ⇒ higher implied growth
    g_low = implied_growth_rate(enterprise_value=1000.0, fcf=50.0, discount_rate=0.10)
    assert g_low is not None
    assert g > g_low


def test_reverse_dcf_implied_ev_roundtrips():
    # Plug the solved g back in and confirm PV(FCF)+PV(TV) ≈ EV.
    ev, fcf, dr, tg, n = 2000.0, 50.0, 0.10, 0.025, 10
    g = implied_growth_rate(ev, fcf, discount_rate=dr, terminal_growth=tg, horizon=n)
    assert g is not None
    pv = sum(fcf * (1 + g) ** y / (1 + dr) ** y for y in range(1, n + 1))
    fcf_term = fcf * (1 + g) ** n * (1 + tg)
    tv = fcf_term / (dr - tg)
    pv += tv / (1 + dr) ** n
    assert pv == pytest.approx(ev, rel=1e-3)


def test_no_formula_returns_nan():
    # Guard: a couple of representative formulas never emit NaN
    for r in (gross_margin(1.0, 3.0), fcf_yield(10.0, 100.0)):
        assert r.value is None or not math.isnan(r.value)
