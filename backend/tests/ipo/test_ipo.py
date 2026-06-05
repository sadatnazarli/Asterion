"""M13 IPO-mode tests — contract enforcement, no network.

Covers the Phase-9 requirements:
  - unverified IPO news does not create an investable score
  - a missing SEC filing returns not_verifiable_yet / wait_for_official_filing
  - negative/unconfirmed FCF uses the scenario model, not a normal reverse DCF
  - valuation math does not run with a missing share count
  - no buy/sell wording in any output
  - all outputs include missing-data flags
  - nothing is invented (empty filing -> all facts None)
"""
from __future__ import annotations

import json

from app.ipo import ipo_valuation, report, risk_analysis
from app.ipo.filing_parser import parse_filing_text
from app.ipo.schemas import (
    VERIFICATION_FOUND,
    VERIFICATION_NONE,
    FilingFacts,
    VerificationResult,
)

# A compact fixture mimicking the SpaceX S-1 summary (no network needed).
FIXTURE = (
    "We are offering 555,555,555 shares of our Class A common stock. "
    "We expect the initial public offering price to be $135.00 per share. "
    "These numbers are based on 6,824,641,355 shares of Class A common stock and "
    "5,695,668,265 shares of Class B common stock outstanding as of March 31, 2026. "
    "We had cash and cash equivalents of $15,852 million as of March 31, 2026. "
    "For the three months ended March 31, 2026, we generated revenue on a consolidated "
    "basis of $4,694 million, loss from operations of $(1,943) million and Adjusted "
    "EBITDA of $1,127 million. For the year ended December 31, 2025, we generated revenue "
    "on a consolidated basis of $18,674 million, loss from operations of $(2,589) million "
    "and Adjusted EBITDA of $6,584 million. Our Class A common stock will have one vote "
    "per share; our Class B common stock will have ten votes per share. The shares may not "
    "be sold during a period of 180 days after the date of this prospectus (the lock-up period)."
)

URL = "https://www.sec.gov/Archives/edgar/data/1181412/x/spacex.htm"


def _verified() -> VerificationResult:
    return VerificationResult(
        query="Space Exploration Technologies Corp",
        status=VERIFICATION_FOUND,
        registrant_name="SPACE EXPLORATION TECHNOLOGIES CORP",
        cik="0001181412",
        proposed_ticker="SPCX",
        filings=[{"form": "S-1", "filing_date": "2026-05-20", "accession": "x", "url": URL}],
    )


# ── parsing / provenance ────────────────────────────────────────────────────
def test_parser_extracts_core_facts_with_provenance():
    f = parse_filing_text(FIXTURE, ticker="SPACEX", source_url=URL)
    assert f.num("ipo_price_per_share") == 135.0
    assert f.num("shares_offered") == 555_555_555
    assert f.num("total_shares_pre_offering") == 6_824_641_355 + 5_695_668_265
    assert f.num("revenue_fy2025") == 18_674
    assert f.num("loss_from_operations_fy2025") == -2_589  # loss kept negative
    assert f.num("revenue_q1_2026") == 4_694
    assert f.num("cash_and_equivalents") == 15_852
    assert f.num("class_b_votes_per_share") == 10.0
    assert f.num("lockup_days") == 180.0
    # provenance snippet retained for audit
    assert f.facts["ipo_price_per_share"].provenance.source_url == URL
    assert f.facts["revenue_fy2025"].provenance.snippet


def test_no_invented_numbers_on_empty_filing():
    f = parse_filing_text("", ticker="SPACEX", source_url=URL)
    for key in ("ipo_price_per_share", "shares_offered", "revenue_fy2025",
                "total_shares_pre_offering", "cash_and_equivalents"):
        assert f.get(key) is None
        assert key in f.missing


# ── valuation guards ────────────────────────────────────────────────────────
def test_missing_share_count_blocks_valuation():
    f = FilingFacts(ticker="SPACEX")
    # only a price, no shares
    from app.ipo.schemas import FilingFact
    f.add(FilingFact("ipo_price_per_share", 135.0, "per_share"))
    val = ipo_valuation.build_valuation(f)
    assert val.can_value is False
    assert "total_shares_pre_offering" in val.missing
    assert "implied_market_cap_musd" not in val.metrics


def test_negative_fcf_uses_scenario_not_reverse_dcf():
    f = parse_filing_text(FIXTURE, ticker="SPACEX", source_url=URL)
    val = ipo_valuation.build_valuation(f)
    assert val.can_value is True
    assert val.fcf_positive is None  # OCF/capex absent -> unconfirmed
    assert val.method == "scenario"
    assert val.method != "reverse_dcf"
    assert len(val.scenarios) == 3
    assert all(s["label"] == "speculative" for s in val.scenarios)
    # sane headline multiple
    evs = val.metrics["ev_to_revenue"]
    assert 80 < evs < 110


# ── classification / contract ───────────────────────────────────────────────
def test_verified_filing_classifies_valuation_risk_watchlist():
    f = parse_filing_text(FIXTURE, ticker="SPACEX", source_url=URL)
    val = ipo_valuation.build_valuation(f)
    sc = risk_analysis.build_scorecard("SPACEX", _verified(), f, val)
    assert sc.classification == "valuation_risk_watchlist"
    assert 0.0 < sc.confidence <= 0.85
    assert sc.missing_data  # always surfaces missing inputs


def test_unverified_news_mode_not_investable():
    f = FilingFacts(ticker="SPACEX")
    val = ipo_valuation.build_valuation(f)
    v = VerificationResult(query="SpaceX", status=VERIFICATION_NONE)
    sc = risk_analysis.build_scorecard("SPACEX", v, f, val, unverified_mode=True)
    assert sc.classification == "not_verifiable_yet"
    assert sc.confidence <= 0.2
    assert sc.valuation.can_value is False
    assert sc.valuation.scenarios == []


def test_missing_filing_returns_wait_for_official():
    f = FilingFacts(ticker="SPACEX")
    val = ipo_valuation.build_valuation(f)
    v = VerificationResult(query="SpaceX", status=VERIFICATION_NONE)
    risks = risk_analysis.assess_risks(f, val)
    cls, conf = risk_analysis.classify(v, f, val, risks, unverified_mode=False)
    assert cls == "wait_for_official_filing"
    assert conf <= 0.2


def test_no_buy_sell_wording_in_outputs():
    f = parse_filing_text(FIXTURE, ticker="SPACEX", source_url=URL)
    val = ipo_valuation.build_valuation(f)
    sc = risk_analysis.build_scorecard("SPACEX", _verified(), f, val)
    import re
    from app.ipo.schemas import CLASSIFICATIONS
    md = report.render_scorecard_md(sc).lower()
    blob = json.dumps(sc.as_dict()).lower()
    # classification is research-only
    assert sc.classification in CLASSIFICATIONS
    # the only allowed whole-word "buy"/"sell" is the "buy/sell" disclaimer phrase
    # ("insider selling", "buyer", etc. are not ratings and must not trip this).
    for text in (md, blob):
        for token in ("buy", "sell"):
            for mt in re.finditer(rf"\b{token}\b", text):
                idx = mt.start()
                assert "buy/sell" in text[max(0, idx - 4): idx + 8], \
                    f"stray '{token}' near: {text[idx-20:idx+20]}"
    # no price targets / ratings
    for forbidden in ("price target", "strong buy", "we recommend", "overweight", "underweight"):
        assert forbidden not in md
