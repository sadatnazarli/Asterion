"""M13a tests: deterministic opportunity ranking + no-advice contract."""
from __future__ import annotations

import json

from app.scanner.ranking import build_opportunity, rank_universe


def _card(ticker, *, confidence=0.75, expgap=50.0, olc=50.0, reflex=30.0,
          fragility=30.0, misund=50.0, classification="wait_for_better_price"):
    def block(score):
        return {"score": score, "confidence": 1.0, "missing": []}
    adv = {}
    if expgap is not None:
        adv["expectations_gap"] = block(expgap)
    if olc is not None:
        adv["operating_leverage_convexity"] = block(olc)
    if reflex is not None:
        adv["reflexivity_risk"] = block(reflex)
    if fragility is not None:
        adv["thesis_fragility"] = block(fragility)
    if misund is not None:
        adv["misunderstood_change"] = block(misund)
    return {
        "ticker": ticker,
        "confidence": confidence,
        "classification": classification,
        "advanced_scores": adv,
    }


def test_strong_name_screens_well_weak_screens_poorly():
    strong = build_opportunity(_card("AAA", expgap=90, olc=95, reflex=5, fragility=10, misund=90))
    weak = build_opportunity(_card("BBB", expgap=5, olc=10, reflex=90, fragility=90, misund=5))
    assert strong.classification == "screens_well"
    assert weak.classification == "screens_poorly"
    assert strong.composite > weak.composite


def test_risk_is_inverted_not_rewarded():
    # Two names identical except reflexivity/fragility risk. Higher risk => lower score.
    low_risk = build_opportunity(_card("LO", reflex=10, fragility=10))
    high_risk = build_opportunity(_card("HI", reflex=90, fragility=90))
    assert low_risk.composite > high_risk.composite
    assert (low_risk.components["safety"] or 0) > (high_risk.components["safety"] or 0)


def test_low_confidence_is_gated_to_insufficient_data():
    # expgap=100 looks great, but confidence 0.0 must not let it screen well.
    o = build_opportunity(_card("ACRS", confidence=0.0, expgap=100, olc=8,
                                reflex=60, fragility=75, misund=0))
    assert o.classification == "insufficient_data"


def test_missing_components_flagged_and_lower_confidence():
    o = build_opportunity(_card("MISS", expgap=None, olc=None, misund=None))
    assert "value" in o.missing and "quality" in o.missing and "change" in o.missing
    # coverage 2/4 => confidence knocked down from 0.75
    assert o.confidence < 0.75


def test_ranking_orders_best_first_insufficient_last():
    cards = [
        _card("MID", expgap=55, olc=55, reflex=40, fragility=40, misund=50),
        _card("TOP", expgap=95, olc=95, reflex=5, fragility=5, misund=95),
        _card("BAD", confidence=0.0, expgap=100, olc=5, reflex=80, fragility=80, misund=0),
    ]
    ranked = rank_universe(cards)
    assert ranked[0].ticker == "TOP"
    assert ranked[-1].ticker == "BAD"  # insufficient_data sorts last
    assert ranked[-1].classification == "insufficient_data"


def test_no_buy_sell_advice_anywhere_in_output():
    cards = [_card(t, expgap=e) for t, e in [("AAA", 95), ("BBB", 5), ("CCC", 50)]]
    blob = json.dumps([o.as_dict() for o in rank_universe(cards)]).lower()
    for banned in ("buy", "sell", "strong buy", "recommend"):
        assert banned not in blob
    # only the sanctioned classifications appear
    allowed = {"screens_well", "neutral", "screens_poorly", "insufficient_data"}
    for o in rank_universe(cards):
        assert o.classification in allowed


def test_composite_only_renormalizes_over_present_components():
    # With only 'value' present (=80), composite should equal 80 (single component).
    o = build_opportunity(_card("ONE", expgap=80, olc=None, reflex=None,
                                fragility=None, misund=None))
    assert o.composite == 80.0
