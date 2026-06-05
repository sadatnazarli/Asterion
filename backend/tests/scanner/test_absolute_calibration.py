"""M14 — absolute (pinned) score-calibration tests."""
from __future__ import annotations

from app.scanner.absolute_calibration import (
    BAND_EDGES,
    anchored_score,
    band_index,
    build_profile,
    calibrate_absolute,
    component_band,
    composite_band,
    composite_grade,
)
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


def test_band_index_edges():
    assert BAND_EDGES == (40.0, 55.0, 70.0, 85.0)
    assert band_index(0) == 0
    assert band_index(39.9) == 0
    assert band_index(40.0) == 1     # edge is inclusive lower bound of next band
    assert band_index(54.9) == 1
    assert band_index(55.0) == 2
    assert band_index(70.0) == 3
    assert band_index(85.0) == 4
    assert band_index(100.0) == 4


def test_band_labels_per_concept():
    assert composite_band(90) == "exceptional"
    assert composite_grade(90) == "A"
    assert composite_band(10) == "weak"
    assert composite_grade(10) == "E"
    # concept-specific labels share the numeric edges
    assert component_band("value", 90) == "deep_value"
    assert component_band("safety", 90) == "fortress"
    assert component_band("quality", 10) == "weak"
    assert component_band("change", 60) == "steady"


def test_anchored_score_rubric_vs_profile():
    # rubric mode (no profile): identity
    assert anchored_score("value", 73.0, None) == 73.0
    # empirical mode: percentile vs the frozen distribution
    profile = {"value": [10.0, 20.0, 30.0, 40.0]}
    assert anchored_score("value", 40.0, profile) == anchored_score("value", 40.0, profile)
    assert anchored_score("value", 40.0, profile) == 87.5   # top of a 4-pt dist (mid-rank)
    assert anchored_score("value", 5.0, profile) == 0.0     # below all


def test_calibrate_absolute_is_universe_independent():
    # A name's bands depend only on its own scores + the pinned reference, never
    # on which peers are in the scan — the defining property of "absolute".
    a = build_opportunity(_card("A", expgap=80, olc=80, reflex=10, fragility=10, misund=80))
    solo = calibrate_absolute([a])
    a_band_solo = a.composite_band
    a_anchored_solo = a.composite_anchored

    a2 = build_opportunity(_card("A", expgap=80, olc=80, reflex=10, fragility=10, misund=80))
    weak = build_opportunity(_card("B", expgap=5, olc=5, reflex=95, fragility=95, misund=5))
    calibrate_absolute([a2, weak])
    assert a2.composite_band == a_band_solo          # unchanged by adding a peer
    assert a2.composite_anchored == a_anchored_solo
    assert solo["method"] == "rubric"
    # strong name lands high, weak name low — fixed bands
    assert a2.composite_band in {"strong", "exceptional"}
    assert weak.composite_band == "weak"
    assert weak.composite_grade == "E"


def test_missing_component_stays_missing():
    card = _card("NOQ", expgap=70.0)
    card["advanced_scores"].pop("operating_leverage_convexity")  # drop quality
    o = build_opportunity(card)
    calibrate_absolute([o])
    assert o.components_anchored["quality"] is None
    assert o.components_band["quality"] is None
    assert o.composite_band is not None  # still computable from present components


def test_build_profile_sorted_and_complete():
    opps = [build_opportunity(_card(f"T{i}", expgap=float(90 - i * 10))) for i in range(4)]
    prof = build_profile(opps)
    assert set(prof) == {"value", "quality", "safety", "change"}
    assert prof["value"] == sorted(prof["value"])       # ascending
    assert len(prof["value"]) == 4


def test_rank_universe_attaches_absolute_layer():
    cards = [_card(f"T{i}", expgap=float(i * 10)) for i in range(10)]
    ranked = rank_universe(cards)
    top = ranked[0]
    assert top.absolute_method == "rubric"
    d = top.as_dict()
    assert "composite_band" in d and "composite_grade" in d
    assert "components_anchored" in d and "components_band" in d
    assert d["absolute_method"] == "rubric"


def test_rank_universe_uses_pinned_profile_when_given():
    cards = [_card(f"T{i}", expgap=float(i * 10)) for i in range(10)]
    profile = {"value": [0.0, 50.0, 100.0], "quality": [50.0], "safety": [70.0], "change": [50.0]}
    ranked = rank_universe(cards, profile=profile)
    assert all(o.absolute_method == "empirical_profile" for o in ranked)
