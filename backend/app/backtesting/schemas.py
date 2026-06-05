"""Typed contracts for the backtesting MVP.

Plain dataclasses, JSON-serialisable. No DB, no LLM. The backtest measures
*relationships* between a ticker's current Asterion scores and its realised
price behaviour over a fixed historical window. It does NOT claim predictive
power — see the look-ahead caveat in evaluation.py and reports/backtest_summary.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class PriceBar:
    """One daily close."""

    d: date
    close: float


@dataclass(frozen=True, slots=True)
class ForwardReturns:
    """Realised forward price stats measured from an anchor (score) date.

    Horizons are in trading days: 1M≈21, 3M≈63, 6M≈126, 12M≈252.
    Any horizon that runs past the available data is ``None`` (not zero).
    """

    anchor_date: date | None
    anchor_close: float | None
    ret_1m: float | None = None
    ret_3m: float | None = None
    ret_6m: float | None = None
    ret_12m: float | None = None
    max_drawdown: float | None = None  # worst peak-to-trough after anchor (≤ 0)
    volatility_annualised: float | None = None  # stdev of daily returns × √252
    bars_available: int = 0


@dataclass(frozen=True, slots=True)
class ScoreSnapshot:
    """The signals pulled from a ticker's current valuation scorecard."""

    ticker: str
    classification: str | None = None
    confidence: float | None = None
    pe_ratio: float | None = None
    expectations_gap: float | None = None
    thesis_fragility: float | None = None
    operating_leverage_convexity: float | None = None
    reflexivity_risk: float | None = None
    high_valuation_risk: bool = False  # classification == valuation_risk_watchlist
    scores_are_placeholder: bool = False  # inputs were mock/hardcoded
    missing: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BacktestRow:
    """One ticker's full backtest record: signals + benchmark-relative outcome."""

    ticker: str
    snapshot: ScoreSnapshot
    forward: ForwardReturns
    benchmark_ticker: str
    benchmark_forward: ForwardReturns
    excess_return_12m: float | None = None  # ret_12m − benchmark ret_12m
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # dates → iso strings for JSON
        for block in ("forward", "benchmark_forward"):
            ad = d[block].get("anchor_date")
            if ad is not None:
                d[block]["anchor_date"] = ad.isoformat()
        return d


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    """Top-level result object written to reports/backtest_summary.json."""

    generated_at: str
    anchor_lookback_days: int
    benchmark_ticker: str
    rows: list[dict[str, Any]]
    findings: dict[str, Any]
    caveats: list[str]
