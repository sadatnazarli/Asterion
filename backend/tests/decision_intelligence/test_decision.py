"""V1 — Verifex + Asterion decision-intelligence tests."""
from __future__ import annotations

import json
import re

from app.decision_intelligence import merger, risk_taxonomy as tax
from app.decision_intelligence.report import render_decision_md
from app.decision_intelligence.schemas import DISCLAIMER
from app.decision_intelligence.service import generate_decision_report
from app.integrations.verifex import client as verifex_client
from app.integrations.verifex import mapper as verifex_mapper
from app.integrations.verifex.schemas import (
    NO_MATCH,
    OK,
    PROVIDER_UNAVAILABLE,
    VerifexMatch,
    VerifexScreenResult,
)


# ── helpers ─────────────────────────────────────────────────────────────────
def _scorecard(*, expgap, quality=70.0, fragility=20.0, confidence=0.8):
    def block(s):
        return {"score": s, "confidence": 1.0, "missing": []}
    return {
        "ticker": "TST",
        "classification": "wait_for_better_price",
        "confidence": confidence,
        "advanced_scores": {
            "expectations_gap": block(expgap),
            "operating_leverage_convexity": block(quality),
            "thesis_fragility": block(fragility),
            "reflexivity_risk": block(30.0),
        },
        "missing_data": [],
    }


def _screen(*categories, name="Test Entity"):
    matches = [VerifexMatch(name=name, match_score=0.9, categories=list(categories),
                            source="demo_list")]
    return VerifexScreenResult(status=OK, query=name, matches=matches)


def _no_match(name="Clean Co"):
    return VerifexScreenResult(status=NO_MATCH, query=name)


# ── 1. missing key does not crash ───────────────────────────────────────────
def test_verifex_missing_key_does_not_crash():
    res = verifex_client.screen_entity("Acme", api_key="", base_url="")
    assert res.status == PROVIDER_UNAVAILABLE
    # and it maps to a non-clean compliance summary
    comp = verifex_mapper.to_compliance_summary(res)
    assert comp.provider_status == PROVIDER_UNAVAILABLE
    assert comp.match_status == "unknown"


# ── 2. no match is not treated as clean ─────────────────────────────────────
def test_no_match_is_not_clean():
    comp = verifex_mapper.to_compliance_summary(_no_match())
    assert comp.provider_status == "ok"
    assert comp.match_status == "no_match"
    assert comp.findings == []
    assert "no match returned by provider" in comp.headline.lower()
    # explicitly NOT asserting the entity is clean
    assert "is clean" not in comp.headline.lower().replace("not a guarantee the entity is clean", "")


# ── 3. sanctions hit forces blocked_by_compliance_signal ────────────────────
def test_sanctions_hit_forces_block():
    fin = merger.build_financial_summary(
        _scorecard(expgap=80.0), entity="Test Entity", ticker="TST", source="x")
    comp = verifex_mapper.to_compliance_summary(_screen("sanctions"))
    report = merger.merge(fin, comp, entity_name="Test Entity", ticker="TST", is_public=True)
    assert report.classification == tax.BLOCKED_BY_COMPLIANCE_SIGNAL
    assert report.combined_risk_level == "critical"


# ── 4. high financial + no compliance hit → financial_risk_watchlist ────────
def test_high_financial_no_compliance_is_financial_watchlist():
    fin = merger.build_financial_summary(
        _scorecard(expgap=10.0), entity="TST", ticker="TST", source="x")
    assert tax.is_severe(tax.max_level([f.level for f in fin.findings]))
    comp = verifex_mapper.to_compliance_summary(_no_match())
    report = merger.merge(fin, comp, entity_name="TST", ticker="TST", is_public=True)
    assert report.classification == tax.FINANCIAL_RISK_WATCHLIST


# ── 5. high financial + compliance warning → combined_risk_watchlist ────────
def test_high_financial_plus_compliance_warning_is_combined():
    fin = merger.build_financial_summary(
        _scorecard(expgap=10.0), entity="TST", ticker="TST", source="x")
    comp = verifex_mapper.to_compliance_summary(_screen("pep"))  # elevated, non-blocking
    assert comp.match_status == "hits"
    report = merger.merge(fin, comp, entity_name="TST", ticker="TST", is_public=True)
    assert report.classification == tax.COMBINED_RISK_WATCHLIST


# ── 6. missing Asterion scorecard → insufficient_data ───────────────────────
def test_missing_scorecard_is_insufficient_data():
    report = generate_decision_report(
        "ZZZZ_NOPE", screen_fn=lambda name: _no_match(name), write=False)
    assert report.financial_summary.available is False
    assert report.classification == tax.INSUFFICIENT_DATA
    assert "asterion_scorecard" in report.missing_data


# ── 7. no buy/sell wording ──────────────────────────────────────────────────
def test_no_buy_sell_wording():
    fin = merger.build_financial_summary(
        _scorecard(expgap=10.0), entity="TST", ticker="TST", source="x")
    comp = verifex_mapper.to_compliance_summary(_screen("pep"))
    report = merger.merge(fin, comp, entity_name="TST", ticker="TST", is_public=True)
    blob = (json.dumps(report.as_dict()) + "\n" + render_decision_md(report)).lower()
    # the disclaimer legitimately says "buy/sell recommendation"; strip it first
    blob = blob.replace(DISCLAIMER.lower(), "").replace("buy/sell", "")
    for token in ("buy", "sell"):
        assert not re.search(rf"\b{token}\b", blob), f"advice word leaked: {token}"
    # classification is always one of the allowed research labels
    assert report.classification in tax.CLASSIFICATIONS


# ── 8. API keys are never printed / serialized ──────────────────────────────
def test_api_key_never_in_serialized_output():
    secret = "vfx_THIS_IS_A_FAKE_SECRET_0000"
    res = verifex_client.screen_entity("Acme", api_key=secret, base_url="")
    dumped = json.dumps(res.as_dict())
    assert secret not in dumped
    # a full decision report likewise never carries the key
    report = generate_decision_report(
        "ZZZZ_NOPE", screen_fn=lambda name: _no_match(name), write=False)
    assert secret not in json.dumps(report.as_dict())
    assert secret not in render_decision_md(report)


# ── 9. no absolute machine path leaks into the report ───────────────────────
def test_no_absolute_path_in_report():
    report = generate_decision_report(
        "META", screen_fn=lambda name: _no_match(name), write=False)
    blob = json.dumps(report.as_dict())
    assert "/Users/" not in blob and "/home/" not in blob
    if report.financial_summary.source:
        assert report.financial_summary.source.startswith("reports/")


# ── extra: levels never silently "none" when missing ────────────────────────
def test_missing_score_is_unknown_not_none():
    assert tax.score_to_level(None) == "unknown"
    assert merger._normalize_level("elevated") == "medium"
    assert merger._normalize_level("weird") == "unknown"
