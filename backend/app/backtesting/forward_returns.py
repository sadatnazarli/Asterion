"""Forward-return and risk math from a price series — pure functions.

Given an ordered list of daily PriceBars and an anchor index, compute realised
forward returns at 1M/3M/6M/12M, max drawdown after the anchor, and annualised
volatility. All horizons that run past the data return ``None``.
"""
from __future__ import annotations

import math

from .schemas import ForwardReturns, PriceBar

# Trading-day horizons.
H_1M, H_3M, H_6M, H_12M = 21, 63, 126, 252


def _ret(bars: list[PriceBar], anchor_i: int, horizon: int) -> float | None:
    """Simple return from anchor to anchor+horizon, or None if out of range."""
    j = anchor_i + horizon
    if j >= len(bars):
        return None
    base = bars[anchor_i].close
    if base == 0:
        return None
    return bars[j].close / base - 1.0


def _max_drawdown(bars: list[PriceBar], anchor_i: int) -> float | None:
    """Worst peak-to-trough decline (≤ 0) over all bars at/after the anchor."""
    window = bars[anchor_i:]
    if len(window) < 2:
        return None
    peak = window[0].close
    worst = 0.0
    for b in window:
        if b.close > peak:
            peak = b.close
        if peak > 0:
            dd = b.close / peak - 1.0
            if dd < worst:
                worst = dd
    return worst


def _annualised_vol(bars: list[PriceBar], anchor_i: int) -> float | None:
    """Stdev of daily simple returns after the anchor, annualised by √252."""
    window = bars[anchor_i:]
    if len(window) < 3:
        return None
    rets: list[float] = []
    for k in range(1, len(window)):
        prev = window[k - 1].close
        if prev == 0:
            continue
        rets.append(window[k].close / prev - 1.0)
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


def anchor_index(bars: list[PriceBar], lookback_trading_days: int) -> int | None:
    """Index of the anchor bar = *lookback_trading_days* before the last bar.

    Returns None if the series is too short to host the anchor.
    """
    if not bars:
        return None
    i = len(bars) - 1 - lookback_trading_days
    return i if i >= 0 else None


def compute_forward_returns(
    bars: list[PriceBar],
    anchor_i: int | None,
) -> ForwardReturns:
    """Bundle every forward stat for a given anchor index."""
    if anchor_i is None or not bars or anchor_i >= len(bars):
        return ForwardReturns(anchor_date=None, anchor_close=None, bars_available=len(bars))
    return ForwardReturns(
        anchor_date=bars[anchor_i].d,
        anchor_close=bars[anchor_i].close,
        ret_1m=_ret(bars, anchor_i, H_1M),
        ret_3m=_ret(bars, anchor_i, H_3M),
        ret_6m=_ret(bars, anchor_i, H_6M),
        ret_12m=_ret(bars, anchor_i, H_12M),
        max_drawdown=_max_drawdown(bars, anchor_i),
        volatility_annualised=_annualised_vol(bars, anchor_i),
        bars_available=len(bars) - anchor_i,
    )
