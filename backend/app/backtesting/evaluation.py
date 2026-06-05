"""Evaluation: turn backtest rows into answers for the validation questions.

Everything here is descriptive statistics on a *small cross-section* (the
current portfolio names). With the look-ahead caveat below, these are
*associations*, not predictions. Functions are pure and deterministic.

LOOK-AHEAD CAVEAT (must stay loud): the score for each ticker is its CURRENT
scorecard, applied retrospectively to a price window that already happened, and
several advanced-score inputs are placeholder constants. So a relationship here
means "names that score X today behaved like Y over the window" — it cannot be
read as "the score predicted the move." Real validation needs point-in-time
historical scores, which Asterion does not yet store.
"""
from __future__ import annotations

import math
from typing import Any

from .schemas import BacktestRow
from .signals import bucket


def _clean(pairs: list[tuple[float | None, float | None]]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for a, b in pairs:
        if a is not None and b is not None:
            xs.append(float(a))
            ys.append(float(b))
    return xs, ys


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation, None if < 3 points or zero variance."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _mean(vals: list[float | None]) -> float | None:
    clean = [v for v in vals if v is not None]
    return sum(clean) / len(clean) if clean else None


def group_compare(
    rows: list[BacktestRow], flag: str, metric: str
) -> dict[str, Any]:
    """Mean of *metric* for rows where bucket[flag] is True vs False."""
    hi: list[float | None] = []
    lo: list[float | None] = []
    for r in rows:
        b = bucket(r.snapshot).get(flag)
        val = getattr(r.forward, metric, None)
        if b is True:
            hi.append(val)
        elif b is False:
            lo.append(val)
    return {
        "metric": metric,
        "high_group_n": len([v for v in hi if v is not None]),
        "low_group_n": len([v for v in lo if v is not None]),
        "high_group_mean": _mean(hi),
        "low_group_mean": _mean(lo),
    }


def evaluate(rows: list[BacktestRow]) -> dict[str, Any]:
    """Answer the six validation questions descriptively."""
    # Q1: high valuation risk → larger drawdowns?
    q1 = group_compare(rows, "high_valuation_risk", "max_drawdown")

    # Q2: high operating leverage → outperform on 12M return?
    q2 = group_compare(rows, "high_operating_leverage", "ret_12m")

    # Q3: high thesis fragility → higher volatility?
    q3 = group_compare(rows, "high_thesis_fragility", "volatility_annualised")

    # Q4: expectations gap vs future drawdown and vs excess return
    gx, gy = _clean([(r.snapshot.expectations_gap, r.forward.max_drawdown) for r in rows])
    ex, ey = _clean([(r.snapshot.expectations_gap, r.excess_return_12m) for r in rows])
    q4 = {
        "corr_gap_vs_drawdown": pearson(gx, gy),
        "corr_gap_vs_excess_return": pearson(ex, ey),
        "n_drawdown": len(gx),
        "n_excess": len(ex),
    }

    # Q5: are thresholds too strict / loose? distribution of classifications.
    dist: dict[str, int] = {}
    for r in rows:
        c = r.snapshot.classification or "none"
        dist[c] = dist.get(c, 0) + 1

    placeholder_n = sum(1 for r in rows if r.snapshot.scores_are_placeholder)

    return {
        "n_tickers": len(rows),
        "q1_valuation_risk_drawdown": q1,
        "q2_operating_leverage_return": q2,
        "q3_thesis_fragility_volatility": q3,
        "q4_expectations_gap_corr": q4,
        "q5_classification_distribution": dist,
        "placeholder_scored_tickers": placeholder_n,
    }
