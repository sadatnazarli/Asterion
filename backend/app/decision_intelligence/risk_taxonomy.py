"""Risk taxonomy — the single source of truth for the combined risk model.

Pure constants + tiny helpers. No I/O. See docs/30 §6.
"""
from __future__ import annotations

# ── domains ─────────────────────────────────────────────────────────────────
FINANCIAL = "financial"
COMPLIANCE = "compliance"

# ── categories ──────────────────────────────────────────────────────────────
FINANCIAL_CATEGORIES: tuple[str, ...] = (
    "valuation_risk",
    "profitability_risk",
    "balance_sheet_risk",
    "thesis_fragility",
    "expectations_gap",
    "concentration_risk",
)

COMPLIANCE_CATEGORIES: tuple[str, ...] = (
    "sanctions_risk",
    "pep_risk",
    "adverse_media_risk",
    "watchlist_risk",
    "regulatory_enforcement_risk",
    "ownership_control_risk",
    "jurisdiction_risk",
)

# ── levels (ordered) ────────────────────────────────────────────────────────
# "unknown" means the input was missing — it is NEVER silently treated as "none".
LEVELS: tuple[str, ...] = ("none", "low", "medium", "high", "critical", "unknown")
_RANK: dict[str, int] = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# Compliance categories whose presence at critical level blocks research.
BLOCKING_COMPLIANCE_CATEGORIES: frozenset[str] = frozenset(
    {"sanctions_risk", "watchlist_risk"}
)

# ── combined classifications (the ONLY allowed outputs) ─────────────────────
CLEAR_FOR_RESEARCH = "clear_for_research"
FINANCIAL_RISK_WATCHLIST = "financial_risk_watchlist"
COMPLIANCE_RISK_WATCHLIST = "compliance_risk_watchlist"
COMBINED_RISK_WATCHLIST = "combined_risk_watchlist"
INSUFFICIENT_DATA = "insufficient_data"
BLOCKED_BY_COMPLIANCE_SIGNAL = "blocked_by_compliance_signal"

CLASSIFICATIONS: tuple[str, ...] = (
    CLEAR_FOR_RESEARCH,
    FINANCIAL_RISK_WATCHLIST,
    COMPLIANCE_RISK_WATCHLIST,
    COMBINED_RISK_WATCHLIST,
    INSUFFICIENT_DATA,
    BLOCKED_BY_COMPLIANCE_SIGNAL,
)


def level_rank(level: str) -> int:
    """Numeric rank for a *known* level; "unknown" ranks below everything (-1)."""
    return _RANK.get(level, -1)


def max_level(levels: list[str]) -> str:
    """Highest known level among ``levels``; "unknown" if none are known."""
    known = [lvl for lvl in levels if lvl in _RANK]
    if not known:
        return "unknown"
    return max(known, key=lambda lvl: _RANK[lvl])


def is_elevated(level: str) -> bool:
    """True for medium/high/critical (a real, actionable concern)."""
    return level_rank(level) >= _RANK["medium"]


def is_severe(level: str) -> bool:
    """True for high/critical."""
    return level_rank(level) >= _RANK["high"]


def score_to_level(score: float | None, *, invert: bool = False) -> str:
    """Map a 0-100 Asterion sub-score to a risk level.

    Default: a *higher* score means a *healthier* signal => *lower* risk.
    ``invert=True`` for scores where higher means more risk (e.g. fragility).
    A missing score returns "unknown" — never "none".
    """
    if score is None:
        return "unknown"
    s = max(0.0, min(100.0, float(score)))
    if invert:
        s = 100.0 - s
    # s is now "health": high s => low risk
    if s >= 70:
        return "none"
    if s >= 55:
        return "low"
    if s >= 40:
        return "medium"
    if s >= 25:
        return "high"
    return "critical"
