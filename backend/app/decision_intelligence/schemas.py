"""Dataclasses for the decision-intelligence layer. Serializable, no behavior."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DISCLAIMER = (
    "Research only. Not investment, legal, or compliance advice, and not a "
    "buy/sell recommendation. Financial signals are deterministic estimates from "
    "SEC-derived scorecards; compliance signals are passed through from the "
    "Verifex provider and must be verified against official sources before any "
    "decision. Missing data is shown as missing; a provider 'no match' is not a "
    "guarantee of a clean entity."
)


@dataclass
class RiskFinding:
    """One risk signal in either domain."""
    category: str           # from risk_taxonomy.{FINANCIAL,COMPLIANCE}_CATEGORIES
    domain: str             # "financial" | "compliance"
    level: str              # none|low|medium|high|critical|unknown
    rationale: str          # short, neutral, evidence-style
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "domain": self.domain,
            "level": self.level,
            "rationale": self.rationale,
            "evidence": self.evidence,
        }


@dataclass
class FinancialSummary:
    """Asterion's half. ``available`` is False when no scorecard was found."""
    entity: str
    ticker: str | None
    available: bool
    source: str | None                 # scorecard path / api ref
    asterion_classification: str | None
    confidence: float
    findings: list[RiskFinding] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    headline: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "ticker": self.ticker,
            "available": self.available,
            "source": self.source,
            "asterion_classification": self.asterion_classification,
            "confidence": round(self.confidence, 2),
            "findings": [f.as_dict() for f in self.findings],
            "missing": self.missing,
            "headline": self.headline,
        }


@dataclass
class ComplianceSummary:
    """Verifex's half.

    ``provider_status``: ok | no_match | provider_unavailable | error
    ``match_status``:    hits | no_match | unknown
    A ``no_match`` is recorded as such — never described as "clean".
    """
    entity: str
    provider_status: str
    match_status: str
    confidence: float
    findings: list[RiskFinding] = field(default_factory=list)
    matches: list[dict[str, Any]] = field(default_factory=list)
    source: str | None = None
    missing: list[str] = field(default_factory=list)
    headline: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "provider_status": self.provider_status,
            "match_status": self.match_status,
            "confidence": round(self.confidence, 2),
            "findings": [f.as_dict() for f in self.findings],
            "matches": self.matches,
            "source": self.source,
            "missing": self.missing,
            "headline": self.headline,
        }


@dataclass
class DecisionReport:
    """The merged decision-intelligence view."""
    entity_name: str
    ticker: str | None
    is_public: bool
    financial_summary: FinancialSummary
    compliance_summary: ComplianceSummary
    combined_risk_level: str
    classification: str                 # from risk_taxonomy.CLASSIFICATIONS
    confidence: float
    missing_data: list[str] = field(default_factory=list)
    evidence_links: list[str] = field(default_factory=list)
    recommended_next_research_steps: list[str] = field(default_factory=list)
    what_would_change_conclusion: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "ticker": self.ticker,
            "is_public": self.is_public,
            "financial_summary": self.financial_summary.as_dict(),
            "compliance_summary": self.compliance_summary.as_dict(),
            "combined_risk_level": self.combined_risk_level,
            "classification": self.classification,
            "confidence": round(self.confidence, 2),
            "missing_data": self.missing_data,
            "evidence_links": self.evidence_links,
            "recommended_next_research_steps": self.recommended_next_research_steps,
            "what_would_change_conclusion": self.what_would_change_conclusion,
            "disclaimer": self.disclaimer,
        }
