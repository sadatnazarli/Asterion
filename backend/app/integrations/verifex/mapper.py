"""Map Verifex provider payloads ↔ Asterion compliance summaries.

Two seams:
- ``parse_provider_payload`` — provider JSON → VerifexScreenResult. The expected
  shape is documented below; re-map when the real Verifex schema is confirmed.
- ``to_compliance_summary`` — VerifexScreenResult → decision-intelligence
  ComplianceSummary, assigning taxonomy categories + risk levels.
"""
from __future__ import annotations

from typing import Any

from app.decision_intelligence import risk_taxonomy as tax
from app.decision_intelligence.schemas import ComplianceSummary, RiskFinding
from app.integrations.verifex.schemas import (
    NO_MATCH,
    OK,
    VerifexMatch,
    VerifexScreenResult,
)

# Provider category tag → (taxonomy compliance category, default level).
# Sanctions/watchlist default to severe so they trip the compliance block.
_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "sanction": ("sanctions_risk", "critical"),
    "sanctions": ("sanctions_risk", "critical"),
    "ofac": ("sanctions_risk", "critical"),
    "watchlist": ("watchlist_risk", "high"),
    "pep": ("pep_risk", "high"),
    "politically_exposed": ("pep_risk", "high"),
    "adverse_media": ("adverse_media_risk", "medium"),
    "adverse-media": ("adverse_media_risk", "medium"),
    "media": ("adverse_media_risk", "medium"),
    "regulatory": ("regulatory_enforcement_risk", "high"),
    "enforcement": ("regulatory_enforcement_risk", "high"),
    "ownership": ("ownership_control_risk", "medium"),
    "control": ("ownership_control_risk", "medium"),
    "jurisdiction": ("jurisdiction_risk", "medium"),
    "country": ("jurisdiction_risk", "medium"),
}


def _coerce_matches(raw_matches: Any) -> list[VerifexMatch]:
    out: list[VerifexMatch] = []
    if not isinstance(raw_matches, list):
        return out
    for m in raw_matches:
        if not isinstance(m, dict):
            continue
        cats = m.get("categories") or m.get("category") or []
        if isinstance(cats, str):
            cats = [cats]
        score = m.get("match_score", m.get("score"))
        out.append(VerifexMatch(
            name=str(m.get("name") or m.get("entity") or "unknown"),
            match_score=float(score) if isinstance(score, (int, float)) else None,
            categories=[str(c).strip().lower() for c in cats],
            country=m.get("country"),
            source=m.get("source") or m.get("list"),
            raw=m,
        ))
    return out


def parse_provider_payload(payload: Any, *, query: str) -> VerifexScreenResult:
    """Provider JSON → VerifexScreenResult.

    Documented expected shape (re-map when the real schema is known)::

        {"matches": [{"name", "score"|"match_score", "categories":[...],
                      "country", "source"}]}

    ``results`` / ``data`` are accepted as aliases for ``matches``. Anything
    unparseable yields a defensive ``no_match`` (provider answered, nothing
    usable) rather than a fake hit.
    """
    if not isinstance(payload, dict):
        return VerifexScreenResult(status=NO_MATCH, query=query,
                                   notes="unrecognized provider payload")
    raw_matches = payload.get("matches")
    if raw_matches is None:
        raw_matches = payload.get("results", payload.get("data"))
    matches = _coerce_matches(raw_matches)
    status = OK if matches else NO_MATCH
    return VerifexScreenResult(status=status, query=query, matches=matches,
                               raw=payload, notes=f"{len(matches)} match(es)")


def to_compliance_summary(result: VerifexScreenResult) -> ComplianceSummary:
    """VerifexScreenResult → ComplianceSummary with taxonomy levels.

    Honesty rules: provider_unavailable/error are reported as such (not clean);
    no_match is explicitly "no match returned by provider".
    """
    entity = result.query
    src = "verifex"

    if result.status == NO_MATCH:
        return ComplianceSummary(
            entity=entity, provider_status="ok", match_status="no_match",
            confidence=0.6, findings=[], matches=[], source=src,
            missing=[],
            headline="No match returned by provider (not a guarantee the entity is clean).",
        )

    if result.status != OK:
        # provider_unavailable or error
        return ComplianceSummary(
            entity=entity, provider_status=result.status, match_status="unknown",
            confidence=0.0, findings=[], matches=[], source=src,
            missing=["verifex_screen"],
            headline=(
                "Compliance not screened — Verifex unavailable. This is NOT a clean "
                "result; configure the provider and re-run."
            ),
        )

    # OK with matches → build findings per distinct taxonomy category.
    by_cat: dict[str, str] = {}   # taxonomy category -> max level
    for m in result.matches:
        for raw_cat in m.categories:
            mapped = _CATEGORY_MAP.get(raw_cat)
            if not mapped:
                continue
            cat, level = mapped
            cur = by_cat.get(cat)
            if cur is None or tax.level_rank(level) > tax.level_rank(cur):
                by_cat[cat] = level
    if not by_cat:
        # matched names but no recognized category → treat as a watchlist-grade hit
        by_cat["watchlist_risk"] = "medium"

    findings = [
        RiskFinding(
            category=cat, domain=tax.COMPLIANCE, level=level,
            rationale=f"Verifex returned a {cat.replace('_', ' ')} signal.",
            evidence=[f"{m.name} [{m.source or 'verifex'}]" for m in result.matches[:4]],
        )
        for cat, level in by_cat.items()
    ]
    cmax = tax.max_level([f.level for f in findings])
    return ComplianceSummary(
        entity=entity, provider_status="ok", match_status="hits",
        confidence=0.7, findings=findings,
        matches=[m.as_dict() for m in result.matches], source=src, missing=[],
        headline=f"{len(result.matches)} Verifex match(es); max compliance risk {cmax}.",
    )
