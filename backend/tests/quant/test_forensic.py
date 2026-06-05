"""Tests for app.quant.forensic — Altman Z-score, Piotroski F-score, accruals.

Pure function tests: no DB, no LLM. Tests cover full computation, partial
data (degraded confidence), and edge cases.
"""
from __future__ import annotations

import pytest

from app.quant.forensic import (
    FORMULA_VERSION,
    accruals_ratio,
    altman_z_score,
    piotroski_f_score,
    quality_of_earnings,
)


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------

class TestAltmanZScore:
    """Classic Altman Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5."""

    def test_healthy_company(self) -> None:
        """Well-capitalised firm should score above 3.0 (safe zone)."""
        r = altman_z_score(
            working_capital=500.0,
            retained_earnings=800.0,
            ebit=300.0,
            market_cap=2000.0,
            total_liabilities=600.0,
            revenue=1500.0,
            total_assets=2000.0,
        )
        assert r.name == "altman_z_score"
        assert r.value is not None
        # X1 = 500/2000 = 0.25 → 1.2*0.25  = 0.300
        # X2 = 800/2000 = 0.40 → 1.4*0.40  = 0.560
        # X3 = 300/2000 = 0.15 → 3.3*0.15  = 0.495
        # X4 = 2000/600 = 3.33 → 0.6*3.33  = 2.000
        # X5 = 1500/2000= 0.75 → 1.0*0.75  = 0.750
        # Z ≈ 4.105
        assert r.value == pytest.approx(4.105, abs=0.01)
        assert r.confidence == 1.0
        assert r.missing_flags == []

    def test_zero_total_assets(self) -> None:
        r = altman_z_score(
            working_capital=500, retained_earnings=800, ebit=300,
            market_cap=2000, total_liabilities=600, revenue=1500,
            total_assets=0,
        )
        assert r.value is None
        assert "total_assets" in r.missing_flags

    def test_none_total_assets(self) -> None:
        r = altman_z_score(
            working_capital=500, retained_earnings=800, ebit=300,
            market_cap=2000, total_liabilities=600, revenue=1500,
            total_assets=None,
        )
        assert r.value is None

    def test_missing_market_cap(self) -> None:
        """Without market_cap, Altman Z cannot be computed (hard requirement)."""
        r = altman_z_score(
            working_capital=500, retained_earnings=800, ebit=300,
            market_cap=None, total_liabilities=600, revenue=1500,
            total_assets=2000,
        )
        assert r.value is None  # hard requirement
        assert "market_cap" in r.missing_flags
        assert r.confidence == 0.0

    def test_missing_liabilities_for_x4(self) -> None:
        """Zero total_liabilities makes X4 undefined → that component treated as 0."""
        r = altman_z_score(
            working_capital=500, retained_earnings=800, ebit=300,
            market_cap=2000, total_liabilities=0, revenue=1500,
            total_assets=2000,
        )
        # X4 can't be computed (div by 0) but other 4 components are fine.
        assert r.value is not None
        assert r.confidence < 1.0
        assert "total_liabilities" in r.missing_flags

    def test_source_fact_ids(self) -> None:
        r = altman_z_score(
            working_capital=500, retained_earnings=800, ebit=300,
            market_cap=2000, total_liabilities=600, revenue=1500,
            total_assets=2000, source_fact_ids=[1, 2, 3],
        )
        assert r.source_fact_ids == [1, 2, 3]


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

class TestPiotoskiFScore:
    """9-point score: 4 profitability + 3 leverage/liquidity + 2 efficiency."""

    def test_perfect_score(self) -> None:
        r = piotroski_f_score(
            net_income=100,
            operating_cash_flow=120,
            roa_current=0.10,
            roa_prior=0.08,
            long_term_debt_current=200,
            long_term_debt_prior=250,
            current_ratio_current=2.0,
            current_ratio_prior=1.8,
            shares_current=1000,
            shares_prior=1000,
            gross_margin_current=0.60,
            gross_margin_prior=0.55,
            asset_turnover_current=0.80,
            asset_turnover_prior=0.75,
        )
        assert r.name == "piotroski_f_score"
        assert r.value == 9  # all criteria met
        assert r.confidence == 1.0
        assert r.missing_flags == []

    def test_worst_score(self) -> None:
        r = piotroski_f_score(
            net_income=-100,
            operating_cash_flow=-50,
            roa_current=-0.05,
            roa_prior=0.08,
            long_term_debt_current=300,
            long_term_debt_prior=250,
            current_ratio_current=1.0,
            current_ratio_prior=1.8,
            shares_current=1200,
            shares_prior=1000,
            gross_margin_current=0.40,
            gross_margin_prior=0.55,
            asset_turnover_current=0.60,
            asset_turnover_prior=0.75,
        )
        # F4: OCF(-50) > NI(-100) = True → 1 point. Everything else fails.
        assert r.value == 1

    def test_partial_data(self) -> None:
        """Only profitability data available — 4 criteria scoreable."""
        r = piotroski_f_score(
            net_income=100,
            operating_cash_flow=120,
            roa_current=0.10,
            roa_prior=0.08,
        )
        assert r.value is not None
        assert r.value <= 4  # at most 4 (profitability only)
        assert r.confidence < 1.0
        assert len(r.missing_flags) > 0

    def test_no_data(self) -> None:
        """All None → score=0, confidence=0."""
        r = piotroski_f_score()
        assert r.value == 0
        assert r.confidence == 0.0

    def test_ocf_less_than_income_fails_f4(self) -> None:
        """F4: OCF > Net Income for quality of earnings."""
        r = piotroski_f_score(
            net_income=100,
            operating_cash_flow=80,  # < 100
            roa_current=0.10,
            roa_prior=0.08,
        )
        # F1=1 (NI>0), F2=1 (OCF>0), F3=1 (ROA improved), F4=0 (OCF < NI)
        assert r.value == 3

    def test_share_dilution_fails_f7(self) -> None:
        """F7: no new shares issued."""
        r = piotroski_f_score(
            net_income=100,
            operating_cash_flow=120,
            roa_current=0.10,
            roa_prior=0.08,
            shares_current=1100,  # diluted
            shares_prior=1000,
        )
        # F1-F4 pass = 4, F7 fails = 0
        # F5,F6 missing
        assert r.value == 4


# ---------------------------------------------------------------------------
# Accruals Ratio
# ---------------------------------------------------------------------------

class TestAccrualsRatio:
    def test_cash_heavy(self) -> None:
        """OCF > NI → negative accruals → good sign."""
        r = accruals_ratio(50.0, 80.0, 500.0)
        assert r.name == "accruals_ratio"
        assert r.value == pytest.approx((50 - 80) / 500)
        assert r.value < 0

    def test_accrual_heavy(self) -> None:
        """NI > OCF → positive accruals → potential red flag."""
        r = accruals_ratio(100.0, 40.0, 500.0)
        assert r.value == pytest.approx((100 - 40) / 500)
        assert r.value > 0

    def test_zero_assets(self) -> None:
        r = accruals_ratio(50.0, 80.0, 0.0)
        assert r.value is None

    def test_none_inputs(self) -> None:
        r = accruals_ratio(None, 80.0, 500.0)
        assert r.value is None


# ---------------------------------------------------------------------------
# Quality of Earnings
# ---------------------------------------------------------------------------

class TestQualityOfEarnings:
    def test_high_quality(self) -> None:
        r = quality_of_earnings(120.0, 100.0)
        assert r.name == "quality_of_earnings"
        assert r.value == pytest.approx(1.20)

    def test_low_quality(self) -> None:
        r = quality_of_earnings(60.0, 100.0)
        assert r.value == pytest.approx(0.60)

    def test_zero_net_income(self) -> None:
        r = quality_of_earnings(60.0, 0.0)
        assert r.value is None

    def test_none_ocf(self) -> None:
        r = quality_of_earnings(None, 100.0)
        assert r.value is None
