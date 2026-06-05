"""Typed contracts for IPO-mode analysis. No I/O, no LLM.

Everything an IPO scorecard touches is a frozen-ish dataclass with ``as_dict()``
so the JSON report is a faithful serialization of the in-memory objects. Each
extracted number is a :class:`FilingFact` carrying provenance + confidence, so
the report can always answer "where did this come from?".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ── Verification (Phase 1) ──────────────────────────────────────────────────
VERIFICATION_FOUND = "official_filing_found"
VERIFICATION_NONE = "no_official_filing"

# ── Classifications (Phase 7). RESEARCH-ONLY — never buy/sell. ───────────────
Classification = Literal[
    "not_verifiable_yet",
    "wait_for_official_filing",
    "speculative_ipo_watchlist",
    "valuation_risk_watchlist",
    "research_candidate",
    "avoid_until_more_data",
    "monitor_after_first_earnings",
]
CLASSIFICATIONS: tuple[str, ...] = (
    "not_verifiable_yet",
    "wait_for_official_filing",
    "speculative_ipo_watchlist",
    "valuation_risk_watchlist",
    "research_candidate",
    "avoid_until_more_data",
    "monitor_after_first_earnings",
)

RiskLevel = Literal["low", "moderate", "elevated", "high", "unknown"]


@dataclass(frozen=True)
class Provenance:
    """Where a fact came from, and how much we trust the extraction."""

    source_url: str | None = None
    section: str | None = None          # e.g. "Prospectus Summary", "Capitalization"
    snippet: str | None = None          # short verbatim excerpt
    confidence: float = 0.0             # 0..1 extraction confidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "section": self.section,
            "snippet": self.snippet,
            "confidence": round(float(self.confidence), 2),
        }


@dataclass(frozen=True)
class FilingFact:
    """One extracted number/string from the filing, with provenance."""

    key: str
    value: float | str | None
    unit: str | None = None             # "usd_millions" | "shares" | "per_share" | "ratio" | "pct"
    period: str | None = None           # e.g. "FY2025", "Q1-2026", "as_of_2026-03-31"
    provenance: Provenance = field(default_factory=Provenance)

    @property
    def present(self) -> bool:
        return self.value is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "period": self.period,
            "provenance": self.provenance.as_dict(),
        }


@dataclass
class FilingFacts:
    """All facts pulled from a filing, keyed by name. Missing keys are honest."""

    ticker: str
    source_url: str | None = None
    facts: dict[str, FilingFact] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    def get(self, key: str) -> float | str | None:
        fact = self.facts.get(key)
        return fact.value if fact else None

    def num(self, key: str) -> float | None:
        v = self.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    def add(self, fact: FilingFact) -> None:
        self.facts[fact.key] = fact
        if not fact.present and fact.key not in self.missing:
            self.missing.append(fact.key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "source_url": self.source_url,
            "facts": {k: v.as_dict() for k, v in self.facts.items()},
            "missing": list(self.missing),
        }


@dataclass
class VerificationResult:
    """Phase 1 — official-source verification outcome."""

    query: str
    status: str                          # VERIFICATION_FOUND | VERIFICATION_NONE
    registrant_name: str | None = None
    cik: str | None = None
    proposed_ticker: str | None = None
    filings: list[dict[str, Any]] = field(default_factory=list)  # form/date/accession/url
    sources_checked: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def filing_found(self) -> bool:
        return self.status == VERIFICATION_FOUND

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "status": self.status,
            "filing_found": self.filing_found,
            "registrant_name": self.registrant_name,
            "cik": self.cik,
            "proposed_ticker": self.proposed_ticker,
            "filings": self.filings,
            "sources_checked": self.sources_checked,
            "notes": self.notes,
        }


@dataclass
class ValuationResult:
    """Phase 4/5 — deterministic IPO valuation. Computes only what inputs allow."""

    can_value: bool
    metrics: dict[str, float | None] = field(default_factory=dict)
    fcf_positive: bool | None = None     # None when FCF can't be computed
    method: str = "none"                 # "multiples" | "reverse_dcf" | "scenario" | "none"
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    comps: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "can_value": self.can_value,
            "method": self.method,
            "fcf_positive": self.fcf_positive,
            "metrics": {k: (None if v is None else round(v, 4)) for k, v in self.metrics.items()},
            "scenarios": self.scenarios,
            "comps": self.comps,
            "missing": self.missing,
            "notes": self.notes,
        }


@dataclass
class RiskFinding:
    """One risk category (Phase 6)."""

    category: str
    level: RiskLevel
    rationale: str
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "level": self.level,
            "rationale": self.rationale,
            "evidence": self.evidence,
        }


@dataclass
class IpoScorecard:
    """Phase 7 — the final research-only verdict. No buy/sell."""

    ticker: str
    classification: str
    confidence: float
    thesis: str
    verification: VerificationResult
    facts: FilingFacts
    valuation: ValuationResult
    risks: list[RiskFinding]
    key_risks: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    must_verify: list[str] = field(default_factory=list)
    would_change_conclusion: list[str] = field(default_factory=list)
    monitoring_checklist: list[str] = field(default_factory=list)
    disclaimer: str = (
        "IPO / private company mode. Not a normal public ticker analysis. "
        "Research only — not investment advice and not a buy/sell recommendation. "
        "All figures are traceable to the cited filing; missing inputs are shown as missing."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "mode": "ipo_private_company",
            "classification": self.classification,
            "confidence": round(float(self.confidence), 2),
            "thesis": self.thesis,
            "verification": self.verification.as_dict(),
            "facts": self.facts.as_dict(),
            "valuation": self.valuation.as_dict(),
            "risks": [r.as_dict() for r in self.risks],
            "key_risks": self.key_risks,
            "missing_data": self.missing_data,
            "must_verify": self.must_verify,
            "would_change_conclusion": self.would_change_conclusion,
            "monitoring_checklist": self.monitoring_checklist,
            "disclaimer": self.disclaimer,
        }
