"""M10 tests: advanced scores use REAL per-ticker inputs, not mock constants.

These avoid a live DB where possible (score functions take plain dicts). The
"regenerated scorecards differ" test reads the generated report JSONs.
"""
from __future__ import annotations

import json
import os

import pytest

from app.scoring.advanced_inputs import AdvancedInputsFetcher
from app.scoring.advanced_scores import (
    calculate_operating_leverage_convexity,
    calculate_reflexivity_risk,
)
from app.scoring.expectations_gap import calculate_expectations_gap
from app.scoring.thesis_fragility import calculate_thesis_fragility

REPORTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports"))
SCORE_KEYS = ["operating_leverage_convexity", "reflexivity_risk", "expectations_gap", "thesis_fragility"]
TICKERS = ["META", "NVDA", "MSFT", "MU", "VRT", "BLK", "PLTR", "ACRS", "V"]


# ── No hardcoded constants in the fetcher ──────────────────────────────────

def test_fetcher_has_no_mock_methods():
    f = AdvancedInputsFetcher()
    assert not hasattr(f, "fetch_m2_ratios")
    assert not hasattr(f, "fetch_m3_rag_data")


def test_fetcher_without_db_returns_missing_not_constants():
    f = AdvancedInputsFetcher()
    out = f.fetch_all_inputs("NVDA")
    # must NOT contain fabricated ratio constants
    assert "gross_margin" not in out
    assert "revenue_growth_yoy" not in out
    assert out.get("_missing")  # explicit missing marker


def test_source_has_no_constant_mock_dict():
    # Guard against re-introducing the old mock table.
    import app.scoring.advanced_inputs as mod
    src = open(mod.__file__).read()
    assert "0.65" not in src and "0.15" not in src  # old mock gross_margin / growth


# ── Inputs are not constant across tickers when data differs ───────────────

def test_operating_leverage_varies_with_real_inputs():
    a = calculate_operating_leverage_convexity({"gross_margin": 0.80, "revenue_growth_yoy": 0.30})
    b = calculate_operating_leverage_convexity({"gross_margin": 0.30, "revenue_growth_yoy": 0.02})
    assert a["score"] != b["score"]


def test_operating_leverage_uses_margin_revenue_trends():
    base = calculate_operating_leverage_convexity({"gross_margin": 0.6, "revenue_growth_yoy": 0.1})
    with_trend = calculate_operating_leverage_convexity({
        "gross_margin": 0.6, "revenue_growth_yoy": 0.1,
        "operating_leverage_ratio": 2.0, "operating_margin_trend": 0.05,
    })
    # the real trend inputs must move the score
    assert with_trend["score"] != base["score"]
    assert "operating_leverage_ratio" in with_trend["inputs_used"]


# ── Missing data degrades confidence ───────────────────────────────────────

def test_missing_input_degrades_confidence():
    full = calculate_reflexivity_risk({"current_ratio": 1.5, "debt_to_equity": 1.0})
    partial = calculate_reflexivity_risk({"current_ratio": 1.5})
    assert full["confidence"] == 1.0
    assert partial["confidence"] == 0.5
    assert "debt_to_equity" in partial["missing_inputs"]


def test_all_missing_zero_confidence():
    r = calculate_reflexivity_risk({})
    assert r["confidence"] == 0.0
    assert r["failure_modes"]


# ── Expectations gap uses reverse-DCF output ───────────────────────────────

def test_expectations_gap_uses_implied_growth():
    high = calculate_expectations_gap({"implied_growth": 0.40, "historical_growth_ttm": 0.10})
    low = calculate_expectations_gap({"implied_growth": 0.05, "historical_growth_ttm": 0.10})
    assert high["score"] > low["score"]  # bigger implied-vs-historical gap ⇒ higher
    assert "implied_growth" in high["inputs_used"]


def test_expectations_gap_legacy_backward_compatible():
    # legacy contract must still hold (pins old unit test)
    r = calculate_expectations_gap({"implied_growth": 0.25, "historical_growth_ttm": 0.15})
    assert r["score"] == 75.0


# ── Thesis fragility uses DCF sensitivity + real blend ─────────────────────

def test_thesis_fragility_legacy_constant_only():
    r = calculate_thesis_fragility({"dcf_sensitivity_impact": 0.8})
    assert r["score"] == 80.0  # legacy path preserved


def test_thesis_fragility_real_blend_differs_from_legacy():
    rich = calculate_thesis_fragility({
        "dcf_sensitivity_impact": 0.8, "pe_ratio": 50.0, "implied_growth": 0.4,
        "historical_growth_ttm": 0.1, "debt_to_equity": 1.5, "volatility": 0.6,
        "max_drawdown": -0.4, "sbc_to_revenue": 0.1,
    })
    # blended multi-factor score is not the bare 80 anymore
    assert rich["score"] != 80.0
    assert "volatility" in rich["inputs_used"]


def test_thesis_fragility_varies_by_ticker_profile():
    fragile = calculate_thesis_fragility({
        "dcf_sensitivity_impact": 0.9, "pe_ratio": 55, "volatility": 0.7, "max_drawdown": -0.5,
    })
    sturdy = calculate_thesis_fragility({
        "dcf_sensitivity_impact": 0.1, "pe_ratio": 12, "volatility": 0.2, "max_drawdown": -0.1,
    })
    assert fragile["score"] > sturdy["score"]


# ── Regenerated scorecards differ across tickers ───────────────────────────

def _load_scorecards():
    cards = {}
    for t in TICKERS:
        p = os.path.join(REPORTS, f"{t}_valuation_scorecard.json")
        if os.path.exists(p):
            with open(p) as f:
                cards[t] = json.load(f)
    return cards


@pytest.mark.skipif(
    not os.path.exists(os.path.join(REPORTS, "NVDA_valuation_scorecard.json")),
    reason="scorecards not generated",
)
def test_regenerated_scorecards_are_real_not_mock():
    cards = _load_scorecards()
    assert len(cards) >= 5
    # real scorecards carry the real_inputs block
    assert all("real_inputs" in c for c in cards.values())


@pytest.mark.skipif(
    not os.path.exists(os.path.join(REPORTS, "NVDA_valuation_scorecard.json")),
    reason="scorecards not generated",
)
def test_regenerated_scorecards_differ_across_tickers():
    cards = _load_scorecards()
    for key in SCORE_KEYS:
        scores = []
        for c in cards.values():
            blk = (c.get("advanced_scores") or {}).get(key) or {}
            if blk.get("score") is not None:
                scores.append(round(blk["score"], 1))
        # at least 3 distinct values across the book (was 1 under mock)
        assert len(set(scores)) >= 3, f"{key} not varying: {scores}"
