"""M12 tests: historical valuation percentiles (pure)."""
from __future__ import annotations

from datetime import date

import pytest

from app.valuation.percentiles import (
    MultiplePoint,
    build_multiple_history,
    percentile_rank,
    valuation_percentiles,
)


def test_percentile_rank_basic():
    sample = [10.0, 20.0, 30.0, 40.0]
    assert percentile_rank(40.0, sample) == 1.0     # highest
    assert percentile_rank(10.0, sample) == 0.25    # lowest of 4
    assert percentile_rank(25.0, sample) == 0.5     # mid


def test_percentile_rank_too_small():
    assert percentile_rank(5.0, [1.0, 2.0]) is None  # < 3 points


def test_build_multiple_history_prices_each_year():
    periods = [
        {"period_end": date(2025, 12, 31), "fiscal_year": 2025, "revenue": 100.0,
         "net_income": 10.0, "fcf": 8.0, "total_debt": 0.0, "cash": 0.0, "shares": 10.0},
        {"period_end": date(2024, 12, 31), "fiscal_year": 2024, "revenue": 80.0,
         "net_income": 8.0, "fcf": 6.0, "total_debt": 0.0, "cash": 0.0, "shares": 10.0},
    ]
    bars = [(date(2025, 12, 30), 20.0), (date(2024, 12, 30), 16.0)]
    hist = build_multiple_history(periods, bars)
    # 2025: mktcap = 20*10 = 200; PE = 200/10 = 20; EV/Rev = 200/100 = 2; P/FCF = 200/8 = 25
    assert hist[0].pe == pytest.approx(20.0)
    assert hist[0].ev_revenue == pytest.approx(2.0)
    assert hist[0].p_fcf == pytest.approx(25.0)


def test_build_multiple_history_missing_price_is_none():
    periods = [{"period_end": date(2020, 12, 31), "fiscal_year": 2020, "revenue": 100.0,
                "net_income": 10.0, "fcf": 8.0, "total_debt": 0.0, "cash": 0.0, "shares": 10.0}]
    bars = [(date(2025, 12, 30), 20.0)]  # far from period_end ⇒ no match
    hist = build_multiple_history(periods, bars)
    assert hist[0].pe is None and hist[0].ev_revenue is None


def test_negative_fcf_yields_no_pfcf():
    periods = [{"period_end": date(2025, 12, 31), "fiscal_year": 2025, "revenue": 100.0,
                "net_income": -5.0, "fcf": -3.0, "total_debt": 0.0, "cash": 0.0, "shares": 10.0}]
    bars = [(date(2025, 12, 30), 20.0)]
    hist = build_multiple_history(periods, bars)
    assert hist[0].p_fcf is None  # negative FCF
    assert hist[0].pe is None     # negative earnings
    assert hist[0].ev_revenue is not None  # revenue still positive


def test_valuation_percentiles_block_and_missing():
    history = [
        MultiplePoint(2024, pe=15.0, ev_revenue=3.0, p_fcf=None),
        MultiplePoint(2023, pe=18.0, ev_revenue=4.0, p_fcf=None),
        MultiplePoint(2022, pe=22.0, ev_revenue=5.0, p_fcf=None),
    ]
    block, missing = valuation_percentiles(
        current={"pe": 25.0, "ev_revenue": 4.0, "p_fcf": 30.0},
        history=history,
    )
    assert "pe" in block
    assert block["pe"]["percentile"] == 1.0  # 25 is richest vs 15/18/22
    assert block["pe"]["n_years"] == 3
    # p_fcf history empty ⇒ flagged missing, not faked
    assert "valuation_percentile_p_fcf" in missing
    assert "p_fcf" not in block
