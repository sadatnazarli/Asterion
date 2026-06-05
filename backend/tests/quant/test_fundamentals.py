"""Tests for app.quant.fundamentals — deterministic fundamental ratio formulas.

Every formula is a pure function: no DB, no LLM. We test:
  1. Correct computation with normal inputs
  2. None handling (missing inputs → value=None, confidence=0, flags)
  3. Division by zero → value=None with 'zero_denominator' flag
  4. Decimal coercion (SEC data often arrives as Decimal)
  5. source_fact_ids pass-through
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.quant.fundamentals import (
    FORMULA_VERSION,
    FormulaResult,
    _safe_div,
    _to_float,
    current_ratio,
    debt_to_equity,
    free_cash_flow_margin,
    gross_margin,
    net_margin,
    operating_margin,
    return_on_assets,
    return_on_equity,
    revenue_growth,
    sbc_to_operating_cash_flow,
    sbc_to_revenue,
    shares_outstanding_change,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestToFloat:
    def test_none_passthrough(self) -> None:
        assert _to_float(None) is None

    def test_int(self) -> None:
        assert _to_float(42) == 42.0

    def test_decimal(self) -> None:
        assert _to_float(Decimal("3.14")) == pytest.approx(3.14)

    def test_str_numeric(self) -> None:
        assert _to_float("100.5") == pytest.approx(100.5)

    def test_str_garbage_returns_none(self) -> None:
        assert _to_float("not-a-number") is None


class TestSafeDiv:
    def test_normal(self) -> None:
        assert _safe_div(10.0, 2.0) == pytest.approx(5.0)

    def test_zero_denominator(self) -> None:
        assert _safe_div(10.0, 0.0) is None

    def test_none_numerator(self) -> None:
        assert _safe_div(None, 2.0) is None

    def test_none_denominator(self) -> None:
        assert _safe_div(10.0, None) is None

    def test_both_none(self) -> None:
        assert _safe_div(None, None) is None


# ---------------------------------------------------------------------------
# Revenue Growth
# ---------------------------------------------------------------------------

class TestRevenueGrowth:
    def test_positive_growth(self) -> None:
        r = revenue_growth(120.0, 100.0)
        assert r.name == "revenue_growth"
        assert r.value == pytest.approx(0.20)
        assert r.confidence == 1.0
        assert r.missing_flags == []
        assert r.formula_version == FORMULA_VERSION

    def test_negative_growth(self) -> None:
        r = revenue_growth(80.0, 100.0)
        assert r.value == pytest.approx(-0.20)

    def test_from_negative_base(self) -> None:
        r = revenue_growth(50.0, -100.0)
        # (50 - (-100)) / abs(-100) = 150/100 = 1.5
        assert r.value == pytest.approx(1.5)

    def test_zero_prior(self) -> None:
        r = revenue_growth(100.0, 0.0)
        assert r.value is None
        assert "zero_denominator" in r.missing_flags

    def test_none_current(self) -> None:
        r = revenue_growth(None, 100.0)
        assert r.value is None
        assert r.confidence == 0.0
        assert "current_revenue" in r.missing_flags

    def test_none_prior(self) -> None:
        r = revenue_growth(100.0, None)
        assert r.value is None
        assert "prior_revenue" in r.missing_flags

    def test_decimal_inputs(self) -> None:
        r = revenue_growth(Decimal("150"), Decimal("100"))
        assert r.value == pytest.approx(0.50)

    def test_source_fact_ids(self) -> None:
        r = revenue_growth(120, 100, source_fact_ids=[1, 2])
        assert r.source_fact_ids == [1, 2]

    def test_inputs_recorded(self) -> None:
        r = revenue_growth(120.0, 100.0)
        assert r.inputs["current_revenue"] == pytest.approx(120.0)
        assert r.inputs["prior_revenue"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Gross Margin
# ---------------------------------------------------------------------------

class TestGrossMargin:
    def test_normal(self) -> None:
        r = gross_margin(60.0, 100.0)
        assert r.name == "gross_margin"
        assert r.value == pytest.approx(0.60)

    def test_zero_revenue(self) -> None:
        r = gross_margin(60.0, 0.0)
        assert r.value is None
        assert "zero_denominator" in r.missing_flags

    def test_none_gross_profit(self) -> None:
        r = gross_margin(None, 100.0)
        assert r.value is None
        assert "gross_profit" in r.missing_flags


# ---------------------------------------------------------------------------
# Operating Margin
# ---------------------------------------------------------------------------

class TestOperatingMargin:
    def test_normal(self) -> None:
        r = operating_margin(30.0, 100.0)
        assert r.name == "operating_margin"
        assert r.value == pytest.approx(0.30)

    def test_negative_margin(self) -> None:
        r = operating_margin(-10.0, 100.0)
        assert r.value == pytest.approx(-0.10)

    def test_none_inputs(self) -> None:
        r = operating_margin(None, None)
        assert r.value is None
        assert r.confidence == 0.0


# ---------------------------------------------------------------------------
# Net Margin
# ---------------------------------------------------------------------------

class TestNetMargin:
    def test_normal(self) -> None:
        r = net_margin(20.0, 100.0)
        assert r.name == "net_margin"
        assert r.value == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# Free Cash Flow Margin
# ---------------------------------------------------------------------------

class TestFCFMargin:
    def test_normal(self) -> None:
        # OCF=80, capex=-20 → FCF = 80 - 20 = 60, margin = 60/100
        r = free_cash_flow_margin(80.0, -20.0, 100.0)
        assert r.name == "fcf_margin"
        assert r.value == pytest.approx(0.60)

    def test_positive_capex_treated_as_outflow(self) -> None:
        # capex=20 (positive) → abs(20) = 20, FCF = 80 - 20 = 60
        r = free_cash_flow_margin(80.0, 20.0, 100.0)
        assert r.value == pytest.approx(0.60)

    def test_zero_revenue(self) -> None:
        r = free_cash_flow_margin(80.0, 20.0, 0.0)
        assert r.value is None

    def test_none_ocf(self) -> None:
        r = free_cash_flow_margin(None, 20.0, 100.0)
        assert r.value is None
        assert "operating_cash_flow" in r.missing_flags


# ---------------------------------------------------------------------------
# ROE / ROA
# ---------------------------------------------------------------------------

class TestROE:
    def test_normal(self) -> None:
        r = return_on_equity(50.0, 200.0)
        assert r.name == "roe"
        assert r.value == pytest.approx(0.25)

    def test_zero_equity(self) -> None:
        r = return_on_equity(50.0, 0.0)
        assert r.value is None


class TestROA:
    def test_normal(self) -> None:
        r = return_on_assets(50.0, 500.0)
        assert r.name == "roa"
        assert r.value == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Current Ratio
# ---------------------------------------------------------------------------

class TestCurrentRatio:
    def test_normal(self) -> None:
        r = current_ratio(200.0, 100.0)
        assert r.name == "current_ratio"
        assert r.value == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Debt to Equity
# ---------------------------------------------------------------------------

class TestDebtToEquity:
    def test_normal(self) -> None:
        r = debt_to_equity(100.0, 200.0)
        assert r.name == "debt_to_equity"
        assert r.value == pytest.approx(0.50)


# ---------------------------------------------------------------------------
# SBC Metrics
# ---------------------------------------------------------------------------

class TestSBCToRevenue:
    def test_normal(self) -> None:
        r = sbc_to_revenue(30.0, 100.0)
        assert r.name == "sbc_to_revenue"
        assert r.value == pytest.approx(0.30)

    def test_none_sbc(self) -> None:
        r = sbc_to_revenue(None, 100.0)
        assert r.value is None


class TestSBCToOCF:
    def test_normal(self) -> None:
        r = sbc_to_operating_cash_flow(20.0, 100.0)
        assert r.name == "sbc_to_ocf"
        assert r.value == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# Shares Outstanding Change
# ---------------------------------------------------------------------------

class TestSharesChange:
    def test_dilution(self) -> None:
        r = shares_outstanding_change(110.0, 100.0)
        assert r.name == "shares_outstanding_change"
        assert r.value == pytest.approx(0.10)

    def test_buyback(self) -> None:
        r = shares_outstanding_change(90.0, 100.0)
        assert r.value == pytest.approx(-0.10)

    def test_none_inputs(self) -> None:
        r = shares_outstanding_change(None, None)
        assert r.value is None
        assert r.confidence == 0.0
