"""Deterministic merge of Asterion financial risk + Verifex compliance risk.

Pure logic: in => FinancialSummary + ComplianceSummary, out => DecisionReport. No
I/O, no LLM, no advice. See docs/30 §6.
"""
from __future__ import annotations

from typing import Any

from app.decision_intelligence import risk_taxonomy as tax
from app.decision_intelligence.schemas import (
    ComplianceSummary,
    DecisionReport,
    FinancialSummary,
    RiskFinding,
)

# IPO risk-engine level words → taxonomy levels.
_LEVEL_ALIASES = {
    "elevated": "medium",
    "moderate": "medium",
    "severe": "critical",
    "watch": "low",
}


def _normalize_level(level: Any) -> str:
    if isinstance(level, str):
        lvl = level.strip().lower()
        if lvl in tax.LEVELS:
            return lvl
        if lvl in _LEVEL_ALIASES:
            return _LEVEL_ALIASES[lvl]
    return "unknown"


def _adv_score(scorecard: dict, key: str) -> float | None:
    block = (scorecard.get("advanced_scores") or {}).get(key)
    if isinstance(block, dict):
        v = block.get("score")
        return float(v) if isinstance(v, (int, float)) else None
    return None


# ── financial summary builders ──────────────────────────────────────────────
def financial_unavailable(entity: str, ticker: str | None, *, reason: str) -> FinancialSummary:
    """No Asterion scorecard found — honest empty summary, not a clean bill."""
    return FinancialSummary(
        entity=entity,
        ticker=ticker,
        available=False,
        source=None,
        asterion_classification=None,
        confidence=0.0,
        findings=[],
        missing=[reason],
        headline="No Asterion scorecard found — financial risk not assessed.",
    )


def build_financial_summary(
    scorecard: dict, *, entity: str, ticker: str | None, source: str | None,
) -> FinancialSummary:
    """Map a public-company valuation scorecard to financial risk findings."""
    findings: list[RiskFinding] = []

    def add(cat: str, level: str, rationale: str, evidence: list[str]):
        findings.append(RiskFinding(cat, tax.FINANCIAL, level, rationale, evidence))

    expgap = _adv_score(scorecard, "expectations_gap")
    quality = _adv_score(scorecard, "operating_leverage_convexity")
    fragility = _adv_score(scorecard, "thesis_fragility")
    reflex = _adv_score(scorecard, "reflexivity_risk")
    red_flags = [str(r) for r in (scorecard.get("red_flags") or [])][:4]

    # valuation: higher expectations-gap score = cheaper = lower valuation risk.
    add("valuation_risk", tax.score_to_level(expgap),
        "Derived from the expectations-gap score (cheaper vs. own fundamentals = lower risk).",
        [f"expectations_gap score={expgap}"] if expgap is not None else ["expectations_gap missing"])
    # profitability: higher operating-leverage score = stronger model = lower risk.
    add("profitability_risk", tax.score_to_level(quality),
        "Derived from the operating-leverage / quality score.",
        [f"operating_leverage_convexity score={quality}"] if quality is not None else ["quality score missing"])
    # thesis fragility: higher fragility score = more risk (inverted).
    frag_ev = [f"thesis_fragility score={fragility}"]
    if reflex is not None:
        frag_ev.append(f"reflexivity_risk score={reflex}")
    add("thesis_fragility", tax.score_to_level(fragility, invert=True),
        "Higher thesis-fragility / reflexivity raises the risk.", frag_ev)
    # expectations gap (priced-in growth lens) — same input, framed as priced-in risk.
    add("expectations_gap", tax.score_to_level(expgap),
        "How much growth the price already assumes; less cushion = higher risk.",
        [f"expectations_gap score={expgap}"] if expgap is not None else ["expectations_gap missing"])
    # balance sheet: no clean balance-sheet score in the scorecard => unknown.
    add("balance_sheet_risk", "unknown",
        "No standalone balance-sheet score in the valuation scorecard.",
        red_flags or ["balance_sheet_signal not in scorecard"])
    # concentration: portfolio-level, not derivable from a single name => unknown.
    add("concentration_risk", "unknown",
        "Concentration is a portfolio-level signal; not derivable from one scorecard.",
        ["requires portfolio context"])

    confidence = scorecard.get("confidence")
    confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
    missing = [str(m) for m in (scorecard.get("missing_data") or [])]
    missing += ["balance_sheet_signal", "portfolio_concentration_context"]

    fmax = tax.max_level([f.level for f in findings])
    n_elev = sum(1 for f in findings if tax.is_elevated(f.level))
    return FinancialSummary(
        entity=entity, ticker=ticker, available=True, source=source,
        asterion_classification=scorecard.get("classification"),
        confidence=confidence, findings=findings, missing=sorted(set(missing)),
        headline=(
            f"Asterion: {scorecard.get('classification') or 'n/a'}; max financial "
            f"risk {fmax}; {n_elev} elevated signal(s); confidence {confidence:.2f}."
        ),
    )


def build_financial_summary_from_ipo(
    scorecard: dict, *, entity: str, ticker: str | None, source: str | None,
) -> FinancialSummary:
    """Map an IPO / private-company scorecard: pass its risk engine through."""
    findings: list[RiskFinding] = []
    for r in (scorecard.get("risks") or []):
        if not isinstance(r, dict):
            continue
        findings.append(RiskFinding(
            category=str(r.get("category") or "unspecified"),
            domain=tax.FINANCIAL,
            level=_normalize_level(r.get("level")),
            rationale=str(r.get("rationale") or ""),
            evidence=[str(e) for e in (r.get("evidence") or [])][:4],
        ))
    confidence = scorecard.get("confidence")
    confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
    missing = [str(m) for m in (scorecard.get("missing_data") or [])]
    fmax = tax.max_level([f.level for f in findings])
    n_elev = sum(1 for f in findings if tax.is_elevated(f.level))
    return FinancialSummary(
        entity=entity, ticker=ticker, available=True, source=source,
        asterion_classification=scorecard.get("classification"),
        confidence=confidence, findings=findings, missing=sorted(set(missing)),
        headline=(
            f"Asterion IPO mode: {scorecard.get('classification') or 'n/a'}; max "
            f"financial risk {fmax}; {n_elev} elevated signal(s); "
            f"confidence {confidence:.2f}."
        ),
    )


# ── merge ───────────────────────────────────────────────────────────────────
def _financial_max(fin: FinancialSummary) -> str:
    return tax.max_level([f.level for f in fin.findings]) if fin.available else "unknown"


def _compliance_max(comp: ComplianceSummary) -> str:
    return tax.max_level([f.level for f in comp.findings])


def _compliance_blocks(comp: ComplianceSummary) -> bool:
    """A severe hit in a blocking category (e.g. sanctions/watchlist) blocks."""
    return any(
        f.category in tax.BLOCKING_COMPLIANCE_CATEGORIES and tax.is_severe(f.level)
        for f in comp.findings
    )


def _classify(fin: FinancialSummary, comp: ComplianceSummary) -> str:
    if _compliance_blocks(comp):
        return tax.BLOCKED_BY_COMPLIANCE_SIGNAL

    fin_severe = fin.available and tax.is_severe(_financial_max(fin))
    comp_elevated = comp.match_status == "hits" and tax.is_elevated(_compliance_max(comp))

    if not fin.available:
        # No financial basis. Compliance alone can flag, otherwise insufficient.
        if comp_elevated:
            return tax.COMPLIANCE_RISK_WATCHLIST
        return tax.INSUFFICIENT_DATA

    if fin_severe and comp_elevated:
        return tax.COMBINED_RISK_WATCHLIST
    if fin_severe:
        return tax.FINANCIAL_RISK_WATCHLIST
    if comp_elevated:
        return tax.COMPLIANCE_RISK_WATCHLIST

    # Financials assessed and not severe. Only "clear" if the provider actually
    # answered with no match — provider_unavailable/error is NOT clearance.
    if comp.provider_status == "ok" and comp.match_status == "no_match":
        return tax.CLEAR_FOR_RESEARCH
    return tax.INSUFFICIENT_DATA


def _combined_confidence(classification: str, fin: FinancialSummary, comp: ComplianceSummary) -> float:
    if classification == tax.BLOCKED_BY_COMPLIANCE_SIGNAL:
        return round(max(comp.confidence, 0.8), 2)
    if fin.available and comp.provider_status in {"ok", "no_match"}:
        return round((fin.confidence + comp.confidence) / 2, 2)
    if fin.available:                       # compliance blind
        return round(fin.confidence * 0.6, 2)
    if comp.provider_status == "ok":        # financial blind
        return round(comp.confidence * 0.6, 2)
    return 0.1


def _next_steps(classification: str, fin: FinancialSummary, comp: ComplianceSummary) -> list[str]:
    steps: list[str] = []
    if classification == tax.BLOCKED_BY_COMPLIANCE_SIGNAL:
        steps.append("Do not proceed. Verify the compliance hit against the official "
                     "sanctions/watchlist source before any further work.")
    if comp.provider_status == "provider_unavailable":
        steps.append("Configure VERIFEX_API_KEY + VERIFEX_API_BASE_URL and re-run the "
                     "compliance screen (currently unavailable).")
    elif comp.match_status == "hits":
        steps.append("Review each Verifex match and confirm it is the same legal entity "
                     "(name collisions are common).")
    if not fin.available:
        steps.append("Generate the Asterion scorecard for this entity to assess financial risk.")
    elif tax.is_severe(_financial_max(fin)):
        steps.append("Drill into the elevated financial signals in the Asterion scorecard "
                     "(valuation / expectations / fragility).")
    if classification == tax.CLEAR_FOR_RESEARCH:
        steps.append("Proceed to deeper research; re-screen if the entity's structure or "
                     "filings change.")
    return steps


def merge(
    fin: FinancialSummary, comp: ComplianceSummary, *,
    entity_name: str, ticker: str | None, is_public: bool,
) -> DecisionReport:
    classification = _classify(fin, comp)

    if classification == tax.BLOCKED_BY_COMPLIANCE_SIGNAL:
        combined_level = "critical"
    else:
        combined_level = tax.max_level([_financial_max(fin), _compliance_max(comp)])

    missing = list(fin.missing)
    missing += list(comp.missing)
    if not fin.available:
        missing.append("asterion_scorecard")
    if comp.provider_status != "ok":
        missing.append(f"verifex_screen:{comp.provider_status}")

    evidence: list[str] = []
    if fin.source:
        evidence.append(f"financial: {fin.source}")
    if comp.source:
        evidence.append(f"compliance: {comp.source}")
    for m in comp.matches[:5]:
        src = m.get("source") or "verifex"
        evidence.append(f"compliance_match: {m.get('name')} [{src}]")

    what_would_change = [
        "A confirmed sanctions/watchlist hit would force a compliance block.",
        "A fresh Asterion scorecard (or filling the missing inputs) would raise "
        "financial confidence.",
        "A configured Verifex endpoint returning a definitive match/no-match would "
        "replace any 'provider unavailable' state.",
    ]

    return DecisionReport(
        entity_name=entity_name,
        ticker=ticker,
        is_public=is_public,
        financial_summary=fin,
        compliance_summary=comp,
        combined_risk_level=combined_level,
        classification=classification,
        confidence=_combined_confidence(classification, fin, comp),
        missing_data=sorted(set(missing)),
        evidence_links=evidence,
        recommended_next_research_steps=_next_steps(classification, fin, comp),
        what_would_change_conclusion=what_would_change,
    )
