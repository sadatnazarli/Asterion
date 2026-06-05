"""IPO-mode orchestration + report persistence (Phases 1-7, output side).

Ties the pure modules together and writes the four report artifacts:
  reports/spacex_source_verification.{md,json}
  reports/<TICKER>_IPO_scorecard.{md,json}

Network I/O (SEC fetch) lives here and in ``filing_parser``; the analysis itself
is pure and unit-tested.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.ipo import filing_parser, ipo_valuation, report, risk_analysis
from app.ipo.schemas import FilingFacts, IpoScorecard, VerificationResult

REPORTS_DIR = PROJECT_ROOT / "reports"

# Known SpaceX identifiers (verified via EDGAR). Passing the CIK avoids a fragile
# name search; verification still re-confirms the live filing list.
SPACEX = {
    "ticker": "SPACEX",
    "proposed_ticker": "SPCX",
    "name": "Space Exploration Technologies Corp",
    "cik": "0001181412",
}


def _write(path: Path, content: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_verification(v: VerificationResult, slug: str = "spacex") -> dict[str, str]:
    j = REPORTS_DIR / f"{slug}_source_verification.json"
    m = REPORTS_DIR / f"{slug}_source_verification.md"
    _write(j, json.dumps(v.as_dict(), indent=2))
    _write(m, report.render_verification_md(v))
    return {"json": str(j), "md": str(m)}


def write_scorecard(sc: IpoScorecard) -> dict[str, str]:
    j = REPORTS_DIR / f"{sc.ticker}_IPO_scorecard.json"
    m = REPORTS_DIR / f"{sc.ticker}_IPO_scorecard.md"
    _write(j, json.dumps(sc.as_dict(), indent=2))
    _write(m, report.render_scorecard_md(sc))
    return {"json": str(j), "md": str(m)}


def analyze_spacex(
    *,
    filing_url: str | None = None,
    unverified_mode: bool = False,
    write: bool = True,
) -> dict[str, Any]:
    """Full SpaceX IPO analysis. Verifies the filing, parses it, values it, classifies it.

    ``unverified_mode`` skips verification/valuation and emits a 'not_verifiable_yet'
    summary (used when treating IPO chatter as unverified news).
    """
    ticker = SPACEX["ticker"]
    proposed = SPACEX["proposed_ticker"]

    if unverified_mode:
        v = VerificationResult(
            query=SPACEX["name"], status="no_official_filing",
            sources_checked=["unverified news (no official source checked)"],
            notes=["Unverified-news mode: no official SEC filing was confirmed in this run."],
        )
        facts = FilingFacts(ticker=ticker)
        val = ipo_valuation.build_valuation(facts)  # can_value=False (no inputs)
        sc = risk_analysis.build_scorecard(ticker, v, facts, val, unverified_mode=True)
        out: dict[str, Any] = {"verification": v.as_dict(), "scorecard": sc.as_dict()}
        if write:
            out["written"] = {"verification": write_verification(v),
                             "scorecard": write_scorecard(sc)}
        return out

    # Phase 1 — verify official source.
    v = filing_parser.verify_sec_registrant(
        SPACEX["name"], ticker=proposed, cik=SPACEX["cik"],
    )

    # Phase 3 — parse the latest IPO filing (or a supplied URL).
    facts = FilingFacts(ticker=ticker)
    url = filing_url or (v.filings[0]["url"] if v.filings else None)
    if url:
        try:
            text = filing_parser.fetch_filing_text(url)
            facts = filing_parser.parse_filing_text(text, ticker=ticker, source_url=url)
        except Exception as exc:  # network/parse — degrade honestly
            v.notes.append(f"Filing fetch/parse failed ({exc}); facts unavailable.")

    # Phase 4/5 — valuation.
    val = ipo_valuation.build_valuation(facts)

    # Phase 6/7 — risks + classification + scorecard.
    sc = risk_analysis.build_scorecard(ticker, v, facts, val)

    out = {"verification": v.as_dict(), "scorecard": sc.as_dict()}
    if write:
        out["written"] = {"verification": write_verification(v),
                         "scorecard": write_scorecard(sc)}
    return out


def load_ipo_scorecard(ticker: str = "SPACEX") -> dict[str, Any] | None:
    """Read a persisted IPO scorecard JSON (for the API/UI)."""
    path = REPORTS_DIR / f"{ticker.upper()}_IPO_scorecard.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
