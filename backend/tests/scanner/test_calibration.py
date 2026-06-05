"""M13 — cross-sectional score-calibration tests."""
from __future__ import annotations

from app.scanner.calibration import MIN_UNIVERSE, calibrate_universe, percentile_rank
from app.scanner.ranking import build_opportunity, rank_universe


def _card(ticker, *, confidence=0.8, expgap=50.0, olc=50.0, reflex=30.0,
          fragility=30.0, misund=50.0):
    def block(s):
        return {"score": s, "confidence": 1.0, "missing": []}
    return {
        "ticker": ticker,
        "confidence": confidence,
        "classification": "wait_for_better_price",
        "advanced_scores": {
            "expectations_gap": block(expgap),
            "operating_leverage_convexity": block(olc),
            "reflexivity_risk": block(reflex),
            "thesis_fragility": block(fragility),
            "misunderstood_change": block(misund),
        },
    }


def test_percentile_rank_midrank():
    assert percentile_rank([10, 20, 30], 10) == 100 * 0.5 / 3
    assert percentile_rank([10, 20, 30], 20) == 50.0
    assert percentile_rank([10, 20, 30], 30) == 100 * 2.5 / 3
    assert percentile_rank([], 5) == 50.0  # empty distribution -> neutral


def test_small_universe_falls_back_to_absolute():
    opps = [build_opportunity(_card(t, expgap=e)) for t, e in [("A", 90), ("B", 10)]]
    meta = calibrate_universe(opps)
    assert meta["method"] == "absolute"
    for o in opps:
        assert o.calibration == "absolute"
        assert o.composite_calibrated == o.composite          # unchanged
        assert o.components_calibrated == o.components
        assert o.percentiles is None


def test_large_universe_calibrates_cross_sectionally():
    # 9 names with a clean spread on the value factor (expectations_gap).
    cards = [_card(f"T{i}", expgap=float(i * 10), olc=float(i * 10),
                   reflex=float(90 - i * 10), fragility=float(90 - i * 10),
                   misund=float(i * 10)) for i in range(9)]
    opps = [build_opportunity(c) for c in cards]
    meta = calibrate_universe(opps)
    assert meta["method"] == "cross_sectional"
    assert meta["universe_valued"] >= MIN_UNIVERSE
    for o in opps:
        assert o.calibration == "cross_sectional"
        assert o.percentiles is not None
        for v in o.components_calibrated.values():
            assert v is None or 0.0 <= v <= 100.0
    # the strongest name (T8) should land at the top percentile, weakest at bottom
    best = max(opps, key=lambda o: o.composite_calibrated)
    worst = min(opps, key=lambda o: o.composite_calibrated)
    assert best.ticker == "T8"
    assert worst.ticker == "T0"
    assert best.composite_calibrated > worst.composite_calibrated


def test_ranking_uses_calibrated_when_universe_large():
    cards = [_card(f"T{i}", expgap=float(i * 11 % 100), olc=float(i * 7 % 100),
                   reflex=float(i * 13 % 100), fragility=float(i * 5 % 100),
                   misund=float(i * 9 % 100)) for i in range(10)]
    ranked = rank_universe(cards)
    assert ranked[0].calibration == "cross_sectional"
    # ordering follows calibrated composite (best first)
    cals = [o.composite_calibrated for o in ranked]
    assert cals == sorted(cals, reverse=True)
    # as_dict surfaces both layers + calibration tag
    d = ranked[0].as_dict()
    assert d["calibration"] == "cross_sectional"
    assert d["composite"] == ranked[0].composite_calibrated
    assert "composite_absolute" in d and "percentiles" in d


def test_missing_component_keeps_missing_after_calibration():
    cards = [_card(f"T{i}", expgap=float(i * 10)) for i in range(8)]
    cards.append(_card("NOQ", expgap=80.0))
    cards[-1]["advanced_scores"].pop("operating_leverage_convexity")  # drop quality
    opps = [build_opportunity(c) for c in cards]
    calibrate_universe(opps)
    noq = next(o for o in opps if o.ticker == "NOQ")
    assert noq.components_calibrated["quality"] is None
    assert noq.percentiles["quality"] is None
    assert "quality" in noq.missing
