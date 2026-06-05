"""M11 tests: Dynamic WACC Phase A (pure, no DB)."""
from __future__ import annotations

import pytest

from app.valuation.wacc import (
    DEFAULT_COST_OF_DEBT,
    DEFAULT_TAX_RATE,
    FALLBACK_WACC,
    THEME_BETA,
    beta_for_symbol,
    compute_wacc,
)


# ── Beta fallbacks by sector/theme ─────────────────────────────────────────

def test_beta_known_themes():
    assert beta_for_symbol("NVDA") == (THEME_BETA["semiconductor"], "sector_fallback:semiconductor")
    assert beta_for_symbol("MSFT")[0] == THEME_BETA["mega_cap_tech"]
    assert beta_for_symbol("V")[0] == THEME_BETA["fintech"]
    assert beta_for_symbol("ACRS")[0] == THEME_BETA["biotech_speculative"]


def test_beta_default_for_unknown_symbol():
    beta, source = beta_for_symbol("ZZZZ")
    assert beta == THEME_BETA["default"]
    assert source == "default"


# ── CAPM cost of equity ────────────────────────────────────────────────────

def test_cost_of_equity_capm():
    r = compute_wacc(
        market_cap=1_000.0, total_debt=0.0, beta=1.0, beta_source="sector_fallback:x",
        interest_expense=None, income_tax=None, pretax_income=None,
        risk_free_rate=0.045, equity_risk_premium=0.05,
    )
    assert r is not None
    # Ke = 0.045 + 1.0 * 0.05 = 0.095; no debt ⇒ WACC == Ke
    assert r.cost_of_equity == pytest.approx(0.095)
    assert r.wacc == pytest.approx(0.095)
    assert r.weight_debt == 0.0


# ── Cost of debt & tax from facts vs fallback ──────────────────────────────

def test_cost_of_debt_and_tax_from_facts():
    r = compute_wacc(
        market_cap=900.0, total_debt=100.0, beta=1.1, beta_source="sector_fallback:x",
        interest_expense=5.0, income_tax=20.0, pretax_income=100.0,
    )
    assert r.cost_of_debt == pytest.approx(0.05)  # 5/100
    assert r.cost_of_debt_source == "interest_expense/total_debt"
    assert r.tax_rate == pytest.approx(0.20)      # 20/100
    assert r.tax_rate_source == "income_tax/pretax"
    assert r.confidence == 1.0
    assert r.missing_flags == []


def test_cost_of_debt_falls_back_when_no_interest():
    r = compute_wacc(
        market_cap=900.0, total_debt=100.0, beta=1.1, beta_source="sector_fallback:x",
        interest_expense=None, income_tax=20.0, pretax_income=100.0,
    )
    assert r.cost_of_debt == DEFAULT_COST_OF_DEBT
    assert r.cost_of_debt_source == "fallback"
    assert "cost_of_debt" in r.missing_flags
    assert r.confidence < 1.0


def test_tax_falls_back_on_negative_pretax():
    # ACRS-like: loss-making ⇒ effective tax meaningless ⇒ fallback.
    r = compute_wacc(
        market_cap=500.0, total_debt=0.0, beta=1.2, beta_source="sector_fallback:biotech_speculative",
        interest_expense=None, income_tax=-1.0, pretax_income=-50.0,
    )
    assert r.tax_rate == DEFAULT_TAX_RATE
    assert r.tax_rate_source == "fallback"
    assert "tax_rate" in r.missing_flags


def test_cost_of_debt_out_of_band_uses_fallback():
    # absurd implied Kd (interest 50 on debt 100 = 50%) ⇒ reject, fallback.
    r = compute_wacc(
        market_cap=900.0, total_debt=100.0, beta=1.0, beta_source="sector_fallback:x",
        interest_expense=50.0, income_tax=20.0, pretax_income=100.0,
    )
    assert r.cost_of_debt == DEFAULT_COST_OF_DEBT
    assert "cost_of_debt_out_of_band" in r.missing_flags


# ── Weights & full WACC identity ───────────────────────────────────────────

def test_wacc_weighted_identity():
    r = compute_wacc(
        market_cap=800.0, total_debt=200.0, beta=1.0, beta_source="sector_fallback:x",
        interest_expense=10.0, income_tax=21.0, pretax_income=100.0,
        risk_free_rate=0.04, equity_risk_premium=0.05,
    )
    ke = 0.04 + 1.0 * 0.05          # 0.09
    kd = 10.0 / 200.0              # 0.05
    tax = 21.0 / 100.0            # 0.21
    w_e, w_d = 0.8, 0.2
    expected = w_e * ke + w_d * kd * (1 - tax)
    assert r.wacc == pytest.approx(expected)
    assert r.weight_equity == pytest.approx(0.8)
    assert r.weight_debt == pytest.approx(0.2)


# ── Cannot weight without market cap ⇒ None (caller keeps 10% fallback) ─────

def test_no_market_cap_returns_none():
    r = compute_wacc(
        market_cap=None, total_debt=100.0, beta=1.0, beta_source="sector_fallback:x",
        interest_expense=5.0, income_tax=20.0, pretax_income=100.0,
    )
    assert r is None


def test_default_beta_costs_confidence():
    generic = compute_wacc(
        market_cap=1000.0, total_debt=0.0, beta=1.1, beta_source="default",
        interest_expense=None, income_tax=None, pretax_income=None,
    )
    themed = compute_wacc(
        market_cap=1000.0, total_debt=0.0, beta=1.1, beta_source="sector_fallback:x",
        interest_expense=None, income_tax=None, pretax_income=None,
    )
    assert generic.confidence < themed.confidence


def test_fallback_wacc_constant_is_ten_percent():
    assert FALLBACK_WACC == 0.10
