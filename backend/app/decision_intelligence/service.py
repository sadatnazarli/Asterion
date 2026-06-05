"""Decision-intelligence orchestration: load Asterion data, screen via Verifex,
merge, and persist. Thin I/O over the pure ``merger`` + ``mapper``.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

from app.core.config import PROJECT_ROOT
from app.decision_intelligence import merger, report
from app.decision_intelligence.schemas import DecisionReport
from app.integrations.verifex import client as verifex_client
from app.integrations.verifex import mapper as verifex_mapper
from app.integrations.verifex.schemas import VerifexScreenResult

logger = logging.getLogger("asterion.decision")

REPORTS_DIR = PROJECT_ROOT / "reports"

# Known private-entity aliases (legal name -> report key). V1 keeps this tiny and
# explicit; entity resolution is V2.
_PRIVATE_ALIASES = {
    "space exploration technologies corp": "SPACEX",
    "spacex": "SPACEX",
}

# Screen function seam (callable) so tests can inject a fake without network.
ScreenFn = Callable[[str], VerifexScreenResult]


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()
    return s or "ENTITY"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _rel(path: Path) -> str:
    """Path relative to the project root — never leak an absolute machine path."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return path.name


def find_valuation_scorecard(ticker: str) -> tuple[dict | None, str | None]:
    path = REPORTS_DIR / f"{ticker.upper()}_valuation_scorecard.json"
    data = _load_json(path)
    return (data, _rel(path)) if data else (None, None)


def find_ipo_scorecard(key: str) -> tuple[dict | None, str | None]:
    path = REPORTS_DIR / f"{key.upper()}_IPO_scorecard.json"
    data = _load_json(path)
    return (data, _rel(path)) if data else (None, None)


def _default_screen(name: str) -> VerifexScreenResult:
    return verifex_client.screen_entity(name)


def generate_decision_report(
    identifier: str,
    *,
    private: bool = False,
    entity_name: str | None = None,
    screen_fn: ScreenFn | None = None,
    write: bool = True,
) -> DecisionReport:
    """Build (and optionally persist) one decision-intelligence report.

    Public: ``identifier`` is a ticker; loads the valuation scorecard.
    Private: ``identifier`` is a legal name; loads the IPO scorecard if present.
    ``screen_fn`` defaults to the live Verifex client (which itself degrades to
    provider_unavailable when unconfigured) and is injectable for tests.
    """
    screen = screen_fn or _default_screen

    if private:
        name = entity_name or identifier
        key = _PRIVATE_ALIASES.get(identifier.strip().lower(), _slug(identifier))
        ipo_card, ipo_src = find_ipo_scorecard(key)
        if ipo_card:
            fin = merger.build_financial_summary_from_ipo(
                ipo_card, entity=name, ticker=None, source=ipo_src)
        else:
            fin = merger.financial_unavailable(
                name, None, reason=f"no IPO scorecard ({key}_IPO_scorecard.json)")
        ticker = None
        is_public = False
        report_key = key
    else:
        ticker = identifier.upper()
        name = entity_name or ticker
        card, src = find_valuation_scorecard(ticker)
        if card:
            fin = merger.build_financial_summary(
                card, entity=name, ticker=ticker, source=src)
        else:
            fin = merger.financial_unavailable(
                name, ticker, reason=f"no valuation scorecard ({ticker}_valuation_scorecard.json)")
        is_public = True
        report_key = ticker

    screen_result = screen(name)
    comp = verifex_mapper.to_compliance_summary(screen_result)

    decision = merger.merge(
        fin, comp, entity_name=name, ticker=ticker, is_public=is_public)

    if write:
        write_report(decision, report_key)
    return decision


def write_report(decision: DecisionReport, key: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    base = REPORTS_DIR / f"decision_intelligence_{key.upper()}"
    try:
        with open(base.with_suffix(".json"), "w", encoding="utf-8") as fh:
            json.dump(decision.as_dict(), fh, indent=2)
        with open(base.with_suffix(".md"), "w", encoding="utf-8") as fh:
            fh.write(report.render_decision_md(decision))
    except OSError as exc:
        logger.warning("decision: could not write report for %s (%s)", key, exc)


def load_decision_report(entity: str) -> dict[str, Any] | None:
    """Load a previously written decision report (for the API)."""
    key = _PRIVATE_ALIASES.get(entity.strip().lower(), entity.upper())
    path = REPORTS_DIR / f"decision_intelligence_{_slug(key)}.json"
    data = _load_json(path)
    if data is None:
        # also try the raw key (already a slug/ticker)
        data = _load_json(REPORTS_DIR / f"decision_intelligence_{entity.upper()}.json")
    return data
