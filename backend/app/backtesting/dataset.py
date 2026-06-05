"""Data loading for the backtest: price history + current score snapshots.

Price history comes from yfinance (daily closes). Score snapshots come from the
deterministic valuation scorecards already written to ``reports/``. Both are
pure reads — nothing is mutated.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta

from .schemas import PriceBar, ScoreSnapshot

log = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports")

# Inputs we know are mock/hardcoded in the current scorecard generator.
# Used only to set the honesty flag on the snapshot.
_PLACEHOLDER_MARKERS = {
    "thesis_fragility": "dcf_sensitivity_impact",
}


def load_price_history(ticker: str, *, lookback_days: int) -> list[PriceBar]:
    """Daily closes for *ticker* over the last *lookback_days* calendar days.

    Returns an empty list on any provider/network error (caller decides what to
    do with a ticker that has no data). Never raises.
    """
    try:
        import yfinance as yf
    except ImportError:  # pragma: no cover
        log.warning("yfinance not installed — no price history")
        return []

    end = date.today()
    start = end - timedelta(days=lookback_days)
    try:
        df = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat(), auto_adjust=True)
    except Exception as exc:  # network / symbol errors
        log.warning("history fetch failed for %s: %s", ticker, exc)
        return []

    if df is None or df.empty:
        return []

    bars: list[PriceBar] = []
    for idx, row in df.iterrows():
        try:
            d = idx.date() if hasattr(idx, "date") else datetime.fromisoformat(str(idx)).date()
            bars.append(PriceBar(d=d, close=float(row["Close"])))
        except Exception:
            continue
    return bars


def _scorecard_path(ticker: str) -> str | None:
    """Resolve the most specific scorecard JSON for a ticker."""
    candidates = [
        f"{ticker.upper()}_valuation_scorecard.json",
        f"{ticker.upper()}_scorecard.json",
    ]
    for name in candidates:
        p = os.path.join(REPORTS_DIR, name)
        if os.path.exists(p):
            return p
    return None


def load_score_snapshot(ticker: str) -> ScoreSnapshot:
    """Read a ticker's current scorecard into a typed signal snapshot.

    Missing files / missing scores degrade gracefully into ``missing`` flags.
    """
    path = _scorecard_path(ticker)
    if path is None:
        return ScoreSnapshot(ticker=ticker, missing=["scorecard_file"])

    try:
        with open(path) as f:
            sc = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("could not read scorecard for %s: %s", ticker, exc)
        return ScoreSnapshot(ticker=ticker, missing=["scorecard_unreadable"])

    adv = sc.get("advanced_scores", {}) or {}
    metrics = sc.get("metrics", {}) or {}

    def adv_score(key: str) -> float | None:
        block = adv.get(key) or {}
        v = block.get("score")
        return float(v) if v is not None else None

    missing: list[str] = []
    for key in ("expectations_gap", "thesis_fragility", "operating_leverage_convexity"):
        if adv_score(key) is None:
            missing.append(key)

    # Post-M10: real scorecards carry a 'real_inputs' block + market_cap. Their
    # absence marks a legacy mock-fed scorecard.
    placeholder = "real_inputs" not in sc

    classification = sc.get("classification")
    return ScoreSnapshot(
        ticker=ticker,
        classification=classification,
        confidence=sc.get("confidence"),
        pe_ratio=metrics.get("pe_ratio"),
        expectations_gap=adv_score("expectations_gap"),
        thesis_fragility=adv_score("thesis_fragility"),
        operating_leverage_convexity=adv_score("operating_leverage_convexity"),
        reflexivity_risk=adv_score("reflexivity_risk"),
        high_valuation_risk=(classification == "valuation_risk_watchlist"),
        scores_are_placeholder=placeholder,
        missing=missing,
    )
