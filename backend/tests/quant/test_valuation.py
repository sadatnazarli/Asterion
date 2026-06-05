"""Tests for app.quant.valuation — deterministic valuation formulas.

Pure function tests: no DB, no LLM. Covers normal computation, None handling,
division by zero, and Decimal coercion.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.quant.valuation import (
    FORMULA_VERSION,
    earnings_yield,
    enterprise_value,
    ev_to_ebitda,
    ev_to_revenue,
    fcf_yield,
    price_to_book,
    price_to_earnings,
    price_to_fcf,
)


# ---------------------------------------------------------------------------
# Enterprise Value
# ---------------------------------------------------------------------------

class TestEnterpriseValue:
    def test_normal(self) -> None:
        r = enterprise_value(1000.0, 200.0, 50.0)
        assert r.name == "enterprise_value"
        assert r.value == pytest.approx(1150.0)
        assert r.confidence == 1.0

    def test_none_market_cap(self) -> None:
        r = enterprise_value(None, 200.0, 50.0)
        assert r.value is None
        assert "market_cap" in r.missing_flags

    def test_none_debt_treated_as_zero(self) -> None:
        r = enterprise_value(1000.0, None, 50.0)
        # debt defaults to 0, cash to 0
        assert r.value is not None
        assert r.confidence < 1.0

    def test_decimal_inputs(self) -> None:
        r = enterprise_value(Decimal("1000"), Decimal("200"), Decimal("50"))
        assert r.value == pytest.approx(1150.0)

    def test_source_fact_ids(self) -> None:
        r = enterprise_value(1000, 200, 50, source_fact_ids=[10, 20, 30])
        assert r.source_fact_ids == [10, 20, 30]


# ---------------------------------------------------------------------------
# EV / Revenue
# ---------------------------------------------------------------------------

class TestEVToRevenue:
    def test_normal(self) -> None:
        r = ev_to_revenue(1150.0, 500.0)
        assert r.name == "ev_to_revenue"
        assert r.value == pytest.approx(2.3)

    def test_zero_revenue(self) -> None:
        r = ev_to_revenue(1150.0, 0.0)
        assert r.value is None
        assert "division_by_zero" in r.missing_flags

    def test_none_ev(self) -> None:
        r = ev_to_revenue(None, 500.0)
        assert r.value is None


# ---------------------------------------------------------------------------
# EV / EBITDA
# ---------------------------------------------------------------------------

class TestEVToEBITDA:
    def test_normal(self) -> None:
        r = ev_to_ebitda(1150.0, 200.0)
        assert r.name == "ev_to_ebitda"
        assert r.value == pytest.approx(5.75)

    def test_zero_ebitda(self) -> None:
        r = ev_to_ebitda(1150.0, 0.0)
        assert r.value is None

    def test_negative_ebitda(self) -> None:
        r = ev_to_ebitda(1150.0, -50.0)
        assert r.value == pytest.approx(1150.0 / -50.0)


# ---------------------------------------------------------------------------
# P/E, P/B, P/FCF
# ---------------------------------------------------------------------------

class TestPriceToEarnings:
    def test_normal(self) -> None:
        r = price_to_earnings(1000.0, 50.0)
        assert r.name == "pe_ratio"
        assert r.value == pytest.approx(20.0)

    def test_negative_earnings(self) -> None:
        r = price_to_earnings(1000.0, -50.0)
        assert r.value == pytest.approx(-20.0)

    def test_zero_earnings(self) -> None:
        r = price_to_earnings(1000.0, 0.0)
        assert r.value is None

    def test_none_market_cap(self) -> None:
        r = price_to_earnings(None, 50.0)
        assert r.value is None
        assert "market_cap" in r.missing_flags


class TestPriceToBook:
    def test_normal(self) -> None:
        r = price_to_book(1000.0, 500.0)
        assert r.name == "pb_ratio"
        assert r.value == pytest.approx(2.0)


class TestPriceToFCF:
    def test_normal(self) -> None:
        r = price_to_fcf(1000.0, 100.0)
        assert r.name == "p_to_fcf"
        assert r.value == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# FCF Yield
# ---------------------------------------------------------------------------

class TestFCFYield:
    def test_normal(self) -> None:
        r = fcf_yield(100.0, 1000.0)
        assert r.name == "fcf_yield"
        assert r.value == pytest.approx(0.10)

    def test_zero_market_cap(self) -> None:
        r = fcf_yield(100.0, 0.0)
        assert r.value is None

    def test_none_fcf(self) -> None:
        r = fcf_yield(None, 1000.0)
        assert r.value is None


# ---------------------------------------------------------------------------
# Earnings Yield
# ---------------------------------------------------------------------------

class TestEarningsYield:
    def test_normal(self) -> None:
        r = earnings_yield(80.0, 1000.0)
        assert r.name == "earnings_yield"
        assert r.value == pytest.approx(0.08)

    def test_zero_ev(self) -> None:
        r = earnings_yield(80.0, 0.0)
        assert r.value is None
