"""Historical valuation percentiles (M12).

Answers "is this name cheap or dear *versus its own history*" without any
cross-sectional model: for each past fiscal year we reconstruct the trailing
multiple from that year's fundamentals priced at the year's period-end close,
then rank today's multiple inside that distribution.

Multiples covered: trailing P/E, EV/Revenue, P/FCF. Each is independent — a
ticker can have a P/E history but no usable P/FCF history (e.g. FCF flipped
sign). Missing or too-short history is reported as such; nothing is faked.

Pure module: no DB, no network. Callers pass in the fundamentals + price bars.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Need at least this many points (incl. current) for a percentile to be meaningful.
_MIN_POINTS = 3
# Match a fiscal period-end to the nearest close within this many days.
_PRICE_MATCH_DAYS = 15


def percentile_rank(value: float, sample: list[float]) -> float | None:
    """Percentile of *value* within *sample* (inclusive), in [0, 1].

    0.0 ⇒ cheapest/lowest ever, 1.0 ⇒ richest/highest ever. Returns None if the
    sample is too small to be meaningful.
    """
    pts = [s for s in sample if s is not None]
    if len(pts) < _MIN_POINTS:
        return None
    at_or_below = sum(1 for s in pts if s <= value)
    return at_or_below / len(pts)


def _nearest_close(period_end: date, price_bars: list[tuple[date, float]]) -> float | None:
    best: tuple[int, float] | None = None
    for d, close in price_bars:
        if close is None or close <= 0:
            continue
        delta = abs((d - period_end).days)
        if delta > _PRICE_MATCH_DAYS:
            continue
        if best is None or delta < best[0]:
            best = (delta, close)
    return best[1] if best else None


@dataclass
class MultiplePoint:
    fiscal_year: int | None
    pe: float | None
    ev_revenue: float | None
    p_fcf: float | None


def build_multiple_history(
    periods: list[dict],
    price_bars: list[tuple[date, float]],
) -> list[MultiplePoint]:
    """Reconstruct trailing P/E, EV/Revenue and P/FCF for each past fiscal year.

    *periods* = per-FY fundamentals dicts (need period_end, fiscal_year, revenue,
    net_income, fcf, total_debt, cash, shares). *price_bars* = (date, close)
    oldest→newest. A multiple is None when its inputs are missing or non-positive.
    """
    out: list[MultiplePoint] = []
    for p in periods:
        pe_v = ev_rev = pfcf_v = None
        shares = p.get("shares")
        close = _nearest_close(p["period_end"], price_bars) if p.get("period_end") else None
        if shares and close:
            mktcap = close * shares
            ni = p.get("net_income")
            if ni and ni > 0:
                pe_v = mktcap / ni
            rev = p.get("revenue")
            if rev and rev > 0:
                debt = p.get("total_debt") or 0.0
                cash = p.get("cash") or 0.0
                ev_rev = (mktcap + debt - cash) / rev
            fcf = p.get("fcf")
            if fcf and fcf > 0:
                pfcf_v = mktcap / fcf
        out.append(MultiplePoint(
            fiscal_year=p.get("fiscal_year"),
            pe=pe_v, ev_revenue=ev_rev, p_fcf=pfcf_v,
        ))
    return out


def valuation_percentiles(
    *,
    current: dict[str, float | None],
    history: list[MultiplePoint],
) -> tuple[dict, list[str]]:
    """Rank each current multiple inside its own history.

    *current* = {"pe", "ev_revenue", "p_fcf"} for today. Returns
    ``(percentiles_block, missing_flags)``. A multiple with too little history is
    omitted from the block and named in missing_flags.
    """
    block: dict[str, dict] = {}
    missing: list[str] = []
    fields = (
        ("pe", "pe"),
        ("ev_revenue", "ev_revenue"),
        ("p_fcf", "p_fcf"),
    )
    for cur_key, attr in fields:
        cur_val = current.get(cur_key)
        sample = [getattr(pt, attr) for pt in history if getattr(pt, attr) is not None]
        if cur_val is None or len(sample) < _MIN_POINTS:
            missing.append(f"valuation_percentile_{cur_key}")
            continue
        # Ensure the current value participates in its own ranking.
        full = sample if cur_val in sample else sample + [cur_val]
        rank = percentile_rank(cur_val, full)
        if rank is None:
            missing.append(f"valuation_percentile_{cur_key}")
            continue
        block[cur_key] = {
            "current": cur_val,
            "percentile": rank,
            "n_years": len(sample),
            "min": min(sample),
            "median": sorted(sample)[len(sample) // 2],
            "max": max(sample),
        }
    return block, missing
