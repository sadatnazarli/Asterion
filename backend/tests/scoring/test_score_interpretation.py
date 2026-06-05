"""Tests for score calibration (direction + bands) and backtest math.

Covers app.scoring.calibration and the pure forward-return helpers in
app.backtesting.forward_returns. No DB, no network.
"""
from __future__ import annotations

import pytest

from app.scoring.calibration import (
    CALIBRATION,
    band_for,
    direction_hint,
    interpret,
    is_concerning,
)
from app.backtesting.forward_returns import (
    anchor_index,
    compute_forward_returns,
)
from app.backtesting.schemas import PriceBar
from datetime import date, timedelta


# ── Bands are positional and exhaustive ───────────────────────────────────

@pytest.mark.parametrize(
    "score,expected",
    [
        (0.0, "low"), (24.9, "low"),
        (25.0, "moderate"), (49.9, "moderate"),
        (50.0, "elevated"), (74.9, "elevated"),
        (75.0, "high"), (100.0, "high"),
        (-10.0, "low"), (130.0, "high"),  # clamped
    ],
)
def test_band_for(score, expected):
    assert band_for(score) == expected


# ── Direction flips the meaning of "high" ──────────────────────────────────

def test_high_is_risk_concerning_when_high():
    assert is_concerning(90.0, "higher_is_risk") is True
    assert is_concerning(10.0, "higher_is_risk") is False


def test_high_is_better_concerning_when_low():
    assert is_concerning(10.0, "higher_is_better") is True
    assert is_concerning(90.0, "higher_is_better") is False


def test_neutral_never_concerning():
    assert is_concerning(90.0, "neutral") is False
    assert is_concerning(10.0, "neutral") is False


# ── Per-score directions match the spec ────────────────────────────────────

def test_operating_leverage_is_higher_is_better():
    assert CALIBRATION["operating_leverage_convexity"].direction == "higher_is_better"
    assert direction_hint("operating_leverage_convexity") == "High is good"


def test_reflexivity_and_fragility_are_risk():
    assert CALIBRATION["reflexivity_risk"].direction == "higher_is_risk"
    assert CALIBRATION["thesis_fragility"].direction == "higher_is_risk"
    assert direction_hint("thesis_fragility") == "High is risk"


def test_expectations_gap_is_risk():
    assert CALIBRATION["expectations_gap"].direction == "higher_is_risk"


def test_every_spec_has_all_four_band_explanations():
    for spec in CALIBRATION.values():
        assert set(spec.band_explanations) == {"low", "moderate", "elevated", "high"}
        assert all(spec.band_explanations.values())  # non-empty


def test_placeholder_scores_flagged_in_calibration():
    # Honesty: no real-fed-but-uncalibrated score may claim production maturity.
    assert CALIBRATION["thesis_fragility"].maturity in ("mvp", "placeholder")
    assert CALIBRATION["operating_leverage_convexity"].maturity in ("mvp", "placeholder")
    assert CALIBRATION["expectations_gap"].maturity in ("mvp", "placeholder")
    # the still-unwired NLP scores stay placeholder
    assert CALIBRATION["narrative_entropy"].maturity == "placeholder"


# ── interpret() contract ───────────────────────────────────────────────────

def test_interpret_known_score():
    out = interpret("thesis_fragility", 80.0)
    assert out["available"] is True
    assert out["band"] == "high"
    assert out["direction"] == "higher_is_risk"
    assert out["concerning"] is True
    assert out["explanation"]


def test_interpret_none_score_degrades():
    out = interpret("thesis_fragility", None)
    assert out["available"] is False
    assert out["concerning"] is False


def test_interpret_unknown_key_degrades():
    out = interpret("not_a_real_score", 50.0)
    assert out["available"] is False


# ── Backtest forward-return math ───────────────────────────────────────────

def _series(prices: list[float]) -> list[PriceBar]:
    d0 = date(2025, 1, 1)
    return [PriceBar(d=d0 + timedelta(days=i), close=p) for i, p in enumerate(prices)]


def test_anchor_index_too_short_returns_none():
    bars = _series([100.0] * 10)
    assert anchor_index(bars, 252) is None


def test_forward_returns_simple_uptrend():
    # 260 bars rising 0 then flat-ish; anchor 252 back = index 7
    prices = [100.0 + i for i in range(260)]  # strictly rising
    bars = _series(prices)
    ai = anchor_index(bars, 252)
    assert ai == len(bars) - 1 - 252
    fwd = compute_forward_returns(bars, ai)
    assert fwd.anchor_close == prices[ai]
    # 1M (21d) forward return is positive in an uptrend
    assert fwd.ret_1m is not None and fwd.ret_1m > 0
    # max drawdown in a strict uptrend is ~0 (never below peep entry-forward peak)
    assert fwd.max_drawdown == pytest.approx(0.0)


def test_forward_returns_handles_short_horizons_as_none():
    # only 30 bars after anchor → 3M/6M/12M unavailable
    bars = _series([100.0 + i for i in range(30)])
    fwd = compute_forward_returns(bars, 0)
    assert fwd.ret_1m is not None
    assert fwd.ret_3m is None
    assert fwd.ret_6m is None
    assert fwd.ret_12m is None


def test_max_drawdown_negative_on_crash():
    # rise to 200 then crash to 100
    prices = [100.0 + i for i in range(100)] + [200.0 - i for i in range(100)]
    bars = _series(prices)
    fwd = compute_forward_returns(bars, 0)
    assert fwd.max_drawdown is not None
    assert fwd.max_drawdown < -0.4  # ~ -50% peak-to-trough


def test_volatility_zero_on_flat_series():
    bars = _series([100.0] * 50)
    fwd = compute_forward_returns(bars, 0)
    assert fwd.volatility_annualised == pytest.approx(0.0)


def test_compute_forward_returns_empty_series_safe():
    fwd = compute_forward_returns([], None)
    assert fwd.anchor_close is None
    assert fwd.ret_1m is None
