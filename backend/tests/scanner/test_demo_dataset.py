"""M15 — guard the public demo dataset (examples/demo/reports).

These run against the *tracked* sample files, not generated reports, so a broken
or empty demo (which would make `make demo` look broken on a fresh clone) fails
CI instead of shipping.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.scanner.calibration import MIN_UNIVERSE
from app.scanner.ranking import rank_universe

DEMO_DIR = Path(__file__).resolve().parents[3] / "examples" / "demo" / "reports"


def _scorecards() -> list[dict]:
    cards = []
    for p in sorted(DEMO_DIR.glob("*_valuation_scorecard.json")):
        with open(p, encoding="utf-8") as fh:
            cards.append(json.load(fh))
    return cards


def test_demo_dir_exists():
    assert DEMO_DIR.is_dir(), f"missing demo dataset: {DEMO_DIR}"


def test_enough_scorecards_for_cross_sectional():
    cards = _scorecards()
    # Need at least MIN_UNIVERSE valued names so the demo shows the real
    # cross-sectional calibration, not the small-universe fallback.
    assert len(cards) >= MIN_UNIVERSE


def test_every_scorecard_parses_and_is_shaped():
    for c in _scorecards():
        assert c.get("ticker"), "scorecard missing ticker"
        assert isinstance(c.get("advanced_scores"), dict)


def test_demo_universe_ranks_and_calibrates():
    ranked = rank_universe(_scorecards())
    assert ranked, "demo universe produced no opportunities"
    assert ranked[0].calibration == "cross_sectional"
    # absolute layer is attached too
    assert ranked[0].composite_grade in {"A", "B", "C", "D", "E"}
    # ordering is by the calibrated screen score, best first
    scores = [o.composite_calibrated for o in ranked if o.composite_calibrated is not None]
    assert scores == sorted(scores, reverse=True)


def test_demo_ipo_scorecard_present_and_research_only():
    ipo = DEMO_DIR / "SPACEX_IPO_scorecard.json"
    assert ipo.is_file()
    data = json.loads(ipo.read_text(encoding="utf-8"))
    assert data.get("ticker", "").upper() in {"SPACEX", "SPCX"}
    assert data.get("classification")  # has a research classification
    # research-only: no advice phrasing anywhere in the scorecard
    blob = json.dumps(data).lower()
    for phrase in ("strong buy", "buy now", "buy rating", "sell rating", "price target"):
        assert phrase not in blob, f"IPO scorecard contains advice phrase: {phrase}"


def test_demo_dataset_has_no_obvious_secrets():
    pat = ("@gmail", "api_key", "apikey", "/Users/", "secret", "/home/")
    for p in DEMO_DIR.glob("*"):
        if p.is_file():
            blob = p.read_text(encoding="utf-8", errors="ignore").lower()
            for token in pat:
                assert token.lower() not in blob, f"{p.name} contains '{token}'"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
