"""Tests for app.quant.scoring_inputs — orchestrator unit tests.

These test the orchestration logic with mocked DB connections. We verify
that fetch_period_data calls the right queries, compute_all_ratios produces
the expected FormulaResult list, and generate_missing_data_report works.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.quant.fundamentals import FormulaResult
from app.quant.scoring_inputs import (
    compute_all_ratios,
    generate_missing_data_report,
)


# ---------------------------------------------------------------------------
# generate_missing_data_report
# ---------------------------------------------------------------------------

class TestMissingDataReport:
    def test_empty_results(self) -> None:
        report = generate_missing_data_report([])
        assert report == {}

    def test_no_missing_data(self) -> None:
        results = [
            FormulaResult(name="roe", value=0.15, inputs={"a": 1}, missing_flags=[]),
            FormulaResult(name="roa", value=0.10, inputs={"b": 2}, missing_flags=[]),
        ]
        report = generate_missing_data_report(results)
        assert report == {}

    def test_some_missing(self) -> None:
        results = [
            FormulaResult(name="roe", value=None, inputs={}, confidence=0.0,
                          missing_flags=["net_income"]),
            FormulaResult(name="roa", value=0.10, inputs={"b": 2}, missing_flags=[]),
            FormulaResult(name="altman_z_score", value=None, inputs={}, confidence=0.0,
                          missing_flags=["market_cap", "total_assets"]),
        ]
        report = generate_missing_data_report(results)
        assert "roe" in report
        assert "net_income" in report["roe"]
        assert "roa" not in report
        assert "altman_z_score" in report
        assert len(report["altman_z_score"]) == 2

    def test_all_missing(self) -> None:
        results = [
            FormulaResult(name="r1", value=None, inputs={}, confidence=0.0,
                          missing_flags=["x"]),
            FormulaResult(name="r2", value=None, inputs={}, confidence=0.0,
                          missing_flags=["y", "z"]),
        ]
        report = generate_missing_data_report(results)
        assert len(report) == 2


# ---------------------------------------------------------------------------
# compute_all_ratios (with mocked fetch_period_data)
# ---------------------------------------------------------------------------

class TestComputeAllRatios:
    """Test that compute_all_ratios calls formulas correctly given period data."""

    def _mock_period_data(self) -> dict:
        """Simulated financial data for a single period."""
        return {
            "revenue": (1000.0, 1),
            "gross_profit": (600.0, 2),
            "operating_income": (200.0, 3),
            "net_income": (150.0, 4),
            "operating_cash_flow": (250.0, 5),
            "capex": (50.0, 6),
            "total_assets": (3000.0, 7),
            "current_assets": (800.0, 8),
            "current_liabilities": (400.0, 9),
            "total_liabilities": (1500.0, 10),
            "shareholders_equity": (1500.0, 11),
            "total_debt": (500.0, 12),
            "cash": (200.0, 13),
            "retained_earnings": (300.0, 14),
            "sbc": (80.0, 15),
            "shares_outstanding": (2000.0, 16),
            "long_term_debt": (400.0, 17),
        }

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_produces_formula_results(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        assert len(results) > 0
        assert all(isinstance(r, FormulaResult) for r in results)

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_includes_margin_ratios(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        names = {r.name for r in results}
        assert "gross_margin" in names
        assert "operating_margin" in names
        assert "net_margin" in names
        assert "fcf_margin" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_includes_balance_sheet_ratios(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        names = {r.name for r in results}
        assert "roe" in names
        assert "roa" in names
        assert "current_ratio" in names
        assert "debt_to_equity" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_includes_sbc_metrics(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        names = {r.name for r in results}
        assert "sbc_to_revenue" in names
        assert "sbc_to_ocf" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_includes_forensic_ratios(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        names = {r.name for r in results}
        assert "altman_z_score" in names
        assert "accruals_ratio" in names
        assert "quality_of_earnings" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_with_prior_period_includes_growth(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(
            conn, company_id=1,
            period_end="2024-12-31",
            prior_period_end="2023-12-31",
        )
        names = {r.name for r in results}
        assert "revenue_growth" in names
        assert "shares_outstanding_change" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_with_prior_period_includes_piotroski(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = self._mock_period_data()
        conn = MagicMock()
        results = compute_all_ratios(
            conn, company_id=1,
            period_end="2024-12-31",
            prior_period_end="2023-12-31",
        )
        names = {r.name for r in results}
        assert "piotroski_f_score" in names

    @patch("app.quant.scoring_inputs.fetch_period_data")
    def test_missing_data_produces_none_values(self, mock_fetch: MagicMock) -> None:
        """When key fields are None, formulas should return value=None."""
        sparse_data = {k: (None, None) for k in self._mock_period_data()}
        mock_fetch.return_value = sparse_data
        conn = MagicMock()
        results = compute_all_ratios(conn, company_id=1, period_end="2024-12-31")
        assert len(results) > 0
        # All should have None values when all inputs are None
        for r in results:
            assert r.value is None
