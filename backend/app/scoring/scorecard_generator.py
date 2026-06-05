"""Generate a valuation scorecard from REAL per-ticker data.

Pulls company_id from the ``tickers`` table, builds real advanced-score inputs
(SEC facts + reverse-DCF + price history), computes the five advanced scores, and
runs the deterministic policy engine. No mock constants anywhere. Used by both
scripts/generate_valuation_scorecard.py and the M10 tests.
"""
from __future__ import annotations

import logging
from typing import Any

import psycopg

from app.decision.policy_engine import evaluate_policy
from app.scoring.advanced_scores import (
    calculate_misunderstood_change,
    calculate_operating_leverage_convexity,
    calculate_reflexivity_risk,
)
from app.scoring.expectations_gap import calculate_expectations_gap
from app.scoring.real_inputs import build_advanced_inputs
from app.scoring.thesis_fragility import calculate_thesis_fragility

log = logging.getLogger(__name__)


def resolve_company(conn: psycopg.Connection, symbol: str) -> tuple[int | None, float | None]:
    """Return (company_id, latest_shares_outstanding) for a ticker symbol."""
    row = conn.execute(
        "SELECT company_id FROM tickers WHERE upper(symbol) = upper(%s) LIMIT 1",
        (symbol,),
    ).fetchone()
    if not row:
        return None, None
    company_id = int(row[0])
    # Prefer point-in-time share-count concepts; fall back to weighted-average
    # (META et al. only tag WeightedAverageNumberOfSharesOutstandingBasic).
    shares = None
    for concept in (
        "EntityCommonStockSharesOutstanding",
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ):
        sh = conn.execute(
            """
            SELECT value FROM financial_facts
             WHERE company_id = %s AND unit = 'shares' AND concept = %s
             ORDER BY period_end DESC, filed DESC LIMIT 1
            """,
            (company_id, concept),
        ).fetchone()
        if sh:
            shares = float(sh[0])
            break
    return company_id, shares


def generate_real_scorecard(
    conn: psycopg.Connection,
    symbol: str,
    *,
    price_history: list[float] | None = None,
    price_bars: list[tuple[Any, float]] | None = None,
    latest_price: float | None = None,
) -> dict[str, Any]:
    """Build a full scorecard dict for *symbol* from real data.

    *price_history* = daily closes oldest→newest (for vol/drawdown). *price_bars*
    = (date, close) oldest→newest, enabling historical valuation percentiles
    (M12). *latest_price* overrides the last close for market-cap (else uses
    price_history[-1]).
    """
    company_id, shares = resolve_company(conn, symbol)
    if company_id is None:
        return {"ticker": symbol.upper(), "error": "ticker_not_found", "advanced_scores": {}}

    px = latest_price
    if px is None and price_history:
        px = price_history[-1]
    market_cap = (px * shares) if (px is not None and shares is not None) else None

    inputs, missing = build_advanced_inputs(
        conn, company_id, symbol.upper(),
        price_history=price_history, price_bars=price_bars, market_cap=market_cap,
    )

    advanced_scores = {
        "operating_leverage_convexity": calculate_operating_leverage_convexity(inputs),
        "reflexivity_risk": calculate_reflexivity_risk(inputs),
        "expectations_gap": calculate_expectations_gap(inputs),
        "thesis_fragility": calculate_thesis_fragility(inputs),
        "misunderstood_change": calculate_misunderstood_change(inputs),
    }

    ratios: dict[str, Any] = {}
    for k in ("gross_margin", "fcf_margin", "net_margin", "operating_margin",
              "debt_to_equity", "current_ratio", "pe_ratio"):
        if inputs.get(k) is not None:
            ratios[k] = inputs[k]

    scorecard = evaluate_policy(
        ratios=ratios,
        advanced_scores=advanced_scores,
        missing_data=list(missing),
        hallucination_failed=False,
        m4_memo_status="Unavailable",
    )

    out = scorecard.model_dump(mode="json")
    out["ticker"] = symbol.upper()
    out["real_inputs"] = {k: v for k, v in inputs.items() if k != "_missing"}
    out["market_cap"] = market_cap
    out["price_used"] = px
    out["input_missing_flags"] = list(missing)
    # Surface valuation discount-rate provenance at the top level (M11).
    out["wacc"] = inputs.get("wacc")
    out["wacc_assumptions"] = inputs.get("wacc_assumptions")
    out["fcf"] = {
        "operating_cash_flow": inputs.get("operating_cash_flow"),
        "capex": inputs.get("capex"),
        "fcf": inputs.get("fcf"),
        "fcf_margin": inputs.get("fcf_margin"),
        "capex_concept": inputs.get("capex_concept"),
        "ocf_concept": inputs.get("ocf_concept"),
        "confidence": inputs.get("fcf_confidence"),
    }
    # M12: WACC input provenance (FRED rate / FMP beta) + own-history percentiles.
    wa = inputs.get("wacc_assumptions") or {}
    out["wacc_source"] = {
        "risk_free_source": wa.get("risk_free_source"),
        "beta_source": wa.get("beta_source"),
        "cost_of_debt_source": wa.get("cost_of_debt_source"),
        "tax_rate_source": wa.get("tax_rate_source"),
        "method": wa.get("method"),
    }
    out["valuation_percentiles"] = inputs.get("valuation_percentiles")
    return out
