"""Build REAL per-ticker advanced-score inputs from DB facts + price history.

Replaces the mock ``AdvancedInputsFetcher`` (which returned identical constants
for every ticker). Everything here is derived from:
  - SEC/XBRL ``financial_facts`` (multi-period fundamentals → trends)
  - reverse-DCF mechanics (implied growth + a real sensitivity spread)
  - daily price history (annualised volatility, max drawdown)

Contract: returns ``(inputs: dict, missing: list[str])``. Missing data is NEVER
faked — the key is simply absent and recorded in ``missing`` so downstream score
functions degrade their confidence. No hardcoded ratio constants.
"""
from __future__ import annotations

import logging
import math
from datetime import date

import psycopg

from app.quant.reverse_dcf import implied_growth_rate, reverse_dcf_sensitivity
from app.valuation.percentiles import build_multiple_history, valuation_percentiles
from app.quant.scoring_inputs import (
    _CONCEPT_CHAINS,
    detect_concept,
    fetch_period_data,
    get_annual_periods,
    _v,
)
from app.valuation.wacc import FALLBACK_WACC, wacc_for_company

log = logging.getLogger(__name__)

DEFAULT_WACC = 0.10  # fixed until M11 dynamic WACC; documented in docs/25
TERMINAL_GROWTH = 0.025


# ── small statistics helpers ───────────────────────────────────────────────

def _slope_sign(series_old_to_new: list[float | None]) -> float | None:
    """Net change (newest − oldest) over the non-None points; None if <2."""
    pts = [x for x in series_old_to_new if x is not None]
    if len(pts) < 2:
        return None
    return pts[-1] - pts[0]


def _cagr(first: float | None, last: float | None, years: int) -> float | None:
    if first is None or last is None or years < 1 or first <= 0 or last <= 0:
        return None
    return (last / first) ** (1.0 / years) - 1.0


def annualised_volatility(closes: list[float]) -> float | None:
    if len(closes) < 5:
        return None
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1]]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


def max_drawdown(closes: list[float]) -> float | None:
    if len(closes) < 2:
        return None
    peak = closes[0]
    worst = 0.0
    for c in closes:
        if c > peak:
            peak = c
        if peak > 0:
            worst = min(worst, c / peak - 1.0)
    return worst


# ── multi-period fundamentals ──────────────────────────────────────────────

def _period_fundamentals(
    conn: psycopg.Connection, company_id: int, period: dict
) -> dict[str, float | None]:
    """Pull the raw line items + derived margins for one annual period."""
    data = fetch_period_data(
        conn, company_id, period["period_end"],
        period.get("fiscal_year"), period.get("fiscal_period"),
    )
    rev = _v(data, "revenue")
    gp = _v(data, "gross_profit")
    oi = _v(data, "operating_income")
    ni = _v(data, "net_income")
    ocf = _v(data, "operating_cash_flow")
    capex = _v(data, "capex")
    ca = _v(data, "current_assets")
    cl = _v(data, "current_liabilities")
    debt = _v(data, "total_debt")
    eq = _v(data, "shareholders_equity")
    sbc = _v(data, "sbc")
    cash = _v(data, "cash")
    shares = _v(data, "shares_outstanding")

    def div(a, b):
        return (a / b) if (a is not None and b not in (None, 0)) else None

    fcf = (ocf - abs(capex)) if (ocf is not None and capex is not None) else None
    return {
        "period_end": period["period_end"],
        "fiscal_year": period.get("fiscal_year"),
        "fiscal_period": period.get("fiscal_period"),
        "revenue": rev,
        "operating_income": oi,
        "net_income": ni,
        "operating_cash_flow": ocf,
        "fcf": fcf,
        "capex": abs(capex) if capex is not None else None,
        "gross_margin": div(gp, rev),
        "operating_margin": div(oi, rev),
        "net_margin": div(ni, rev),
        "fcf_margin": div(fcf, rev),
        "current_ratio": div(ca, cl),
        "debt_to_equity": div(debt, eq),
        "sbc_to_revenue": div(sbc, rev),
        "total_debt": debt,
        "cash": cash,
        "shares": shares,
    }


def build_advanced_inputs(
    conn: psycopg.Connection,
    company_id: int,
    symbol: str,
    *,
    price_history: list[float] | None = None,
    price_bars: list[tuple[date, float]] | None = None,
    market_cap: float | None = None,
    max_periods: int = 4,
) -> tuple[dict[str, float | bool], list[str]]:
    """Compute all real advanced-score inputs for one company.

    *price_history* is a list of daily closes (oldest→newest) for vol/drawdown.
    *market_cap* enables EV / reverse-DCF / PE. Both optional — absence degrades
    confidence rather than fabricating values.
    """
    missing: list[str] = []
    out: dict[str, float | bool] = {}

    raw_periods = get_annual_periods(conn, company_id, limit=max_periods * 3)
    if not raw_periods:
        return {}, ["no_annual_periods"]

    # Dedup by fiscal_year — ingestion can emit several period_ends per FY.
    # raw_periods is period_end DESC, so the first row per fiscal_year is its
    # latest filing; keep that one to get clean year-over-year comparisons.
    periods: list[dict] = []
    seen_years: set = set()
    for p in raw_periods:
        fy = p.get("fiscal_year")
        if fy in seen_years:
            continue
        seen_years.add(fy)
        periods.append(p)
        if len(periods) >= max_periods:
            break

    # newest → oldest as returned; build oldest→newest trend series too
    fund = [_period_fundamentals(conn, company_id, p) for p in periods]
    newest = fund[0]
    oldest = fund[-1]
    n_years = max(1, len(fund) - 1)

    # --- latest-level ratios (real, per-ticker) ----------------------------
    for key in ("gross_margin", "operating_margin", "net_margin", "fcf_margin",
                "current_ratio", "debt_to_equity", "sbc_to_revenue"):
        if newest.get(key) is not None:
            out[key] = newest[key]
        else:
            missing.append(key)

    # --- growth + trends ----------------------------------------------------
    rev_new, rev_prev = newest.get("revenue"), (fund[1].get("revenue") if len(fund) > 1 else None)
    if rev_new is not None and rev_prev not in (None, 0):
        out["revenue_growth_yoy"] = rev_new / rev_prev - 1.0
    else:
        missing.append("revenue_growth_yoy")

    oi_new, oi_prev = newest.get("operating_income"), (fund[1].get("operating_income") if len(fund) > 1 else None)
    if oi_new is not None and oi_prev not in (None, 0) and oi_prev > 0:
        out["operating_income_growth_yoy"] = oi_new / oi_prev - 1.0

    # operating-leverage ratio: op income growth vs revenue growth (>1 = convex)
    if "operating_income_growth_yoy" in out and out.get("revenue_growth_yoy", 0) not in (0, None):
        rg = out["revenue_growth_yoy"]
        if rg and rg > 0:
            out["operating_leverage_ratio"] = out["operating_income_growth_yoy"] / rg

    # revenue CAGR + fcf growth as a blended "historical reality"
    rev_cagr = _cagr(oldest.get("revenue"), newest.get("revenue"), n_years)
    if rev_cagr is not None:
        out["revenue_cagr"] = rev_cagr
    fcf_growth = _cagr(oldest.get("fcf"), newest.get("fcf"), n_years)
    if fcf_growth is not None:
        out["fcf_growth"] = fcf_growth
    capex_cagr = _cagr(oldest.get("capex"), newest.get("capex"), n_years)
    if capex_cagr is not None:
        out["capex_growth"] = capex_cagr

    # margin-trend signs (oldest→newest), used by op-leverage + fragility
    for mkey, okey in (("gross_margin", "gross_margin_trend"),
                       ("operating_margin", "operating_margin_trend"),
                       ("fcf_margin", "fcf_margin_trend")):
        slope = _slope_sign([f.get(mkey) for f in reversed(fund)])
        if slope is not None:
            out[okey] = slope

    # share dilution (newest vs oldest shares)
    if newest.get("shares") and oldest.get("shares"):
        out["shares_change"] = newest["shares"] / oldest["shares"] - 1.0

    # blended historical growth = mean of available revenue/fcf growth measures
    hist_components = [v for v in (out.get("revenue_growth_yoy"), rev_cagr, fcf_growth) if v is not None]
    if hist_components:
        out["historical_growth_ttm"] = sum(hist_components) / len(hist_components)
    else:
        missing.append("historical_growth_ttm")

    # --- free cash flow (M11: real OCF − capex, with provenance) -----------
    ocf_new = newest.get("operating_cash_flow")
    capex_new = newest.get("capex")
    fcf_new = newest.get("fcf")
    pe = newest.get("period_end")
    fy = newest.get("fiscal_year")
    fp = newest.get("fiscal_period")
    if ocf_new is not None:
        out["operating_cash_flow"] = ocf_new
        out["ocf_concept"] = detect_concept(conn, company_id, _CONCEPT_CHAINS["operating_cash_flow"], pe, fiscal_year=fy, fiscal_period=fp)
    else:
        missing.append("operating_cash_flow")
    if capex_new is not None:
        out["capex"] = capex_new
        out["capex_concept"] = detect_concept(conn, company_id, _CONCEPT_CHAINS["capex"], pe, fiscal_year=fy, fiscal_period=fp)
    else:
        missing.append("capex")
    if fcf_new is not None:
        out["fcf"] = fcf_new
        # fcf confidence: 1.0 when both legs real, degraded if either source soft
        out["fcf_confidence"] = 1.0 if (ocf_new is not None and capex_new is not None) else 0.5
    else:
        missing.append("fcf")

    # --- valuation + reverse DCF -------------------------------------------
    ni_new = newest.get("net_income")
    if market_cap is not None and ni_new not in (None, 0):
        out["pe_ratio"] = market_cap / ni_new
    elif market_cap is None:
        missing.append("market_cap")

    ev = None
    if market_cap is not None:
        debt = newest.get("total_debt") or 0.0
        cash = newest.get("cash") or 0.0
        ev = market_cap + debt - cash
        out["enterprise_value"] = ev

    # --- dynamic WACC (M11 Phase A) ----------------------------------------
    discount = DEFAULT_WACC
    wacc_res = wacc_for_company(
        conn, company_id, symbol,
        market_cap=market_cap, total_debt=newest.get("total_debt"),
        period_end=pe, fiscal_year=fy, fiscal_period=fp,
    )
    if wacc_res is not None:
        discount = wacc_res.wacc
        out["wacc"] = wacc_res.wacc
        out["wacc_confidence"] = wacc_res.confidence
        out["wacc_assumptions"] = wacc_res.as_dict()
    else:
        out["wacc"] = FALLBACK_WACC
        out["wacc_assumptions"] = {"method": "fallback", "wacc": FALLBACK_WACC}
        missing.append("wacc")

    if ev is not None and fcf_new is not None and fcf_new > 0:
        ig = implied_growth_rate(ev, fcf_new, discount_rate=discount, terminal_growth=TERMINAL_GROWTH)
        if ig is not None:
            out["implied_growth"] = ig
            # Real DCF sensitivity: spread of implied growth across a WACC grid
            # CENTERED on the dynamic WACC, normalised to 0–1. Wider spread ⇒
            # thesis depends more on the discount-rate assumption.
            grid = [discount + d for d in (-0.02, -0.01, 0.0, 0.01, 0.02)
                    if discount + d > TERMINAL_GROWTH]
            sens = reverse_dcf_sensitivity(ev, fcf_new, discount_rates=grid or None)
            vals = [g for row in sens["implied_growth_matrix"] for g in row if g is not None]
            if len(vals) >= 2:
                spread = max(vals) - min(vals)
                out["dcf_sensitivity_impact"] = max(0.0, min(1.0, spread / 0.20))
        else:
            missing.append("implied_growth")
    else:
        missing.append("implied_growth")
        missing.append("dcf_sensitivity_impact")

    # --- historical valuation percentiles (M12) ----------------------------
    # Rank today's multiples against this name's OWN 3–6Y history. Needs dated
    # price bars to price each past period-end; absent them, simply skipped.
    if price_bars:
        # Build a deeper per-FY series than the 4 used for trends (up to ~6Y).
        pct_periods: list[dict] = []
        seen_pct: set = set()
        for p in raw_periods:
            fyx = p.get("fiscal_year")
            if fyx in seen_pct:
                continue
            seen_pct.add(fyx)
            pct_periods.append(_period_fundamentals(conn, company_id, p))
            if len(pct_periods) >= 6:
                break
        history = build_multiple_history(pct_periods, price_bars)
        cur_pe = out.get("pe_ratio")
        cur_ev_rev = (ev / newest["revenue"]) if (ev is not None and newest.get("revenue")) else None
        cur_pfcf = (market_cap / fcf_new) if (market_cap is not None and fcf_new and fcf_new > 0) else None
        block, pct_missing = valuation_percentiles(
            current={"pe": cur_pe, "ev_revenue": cur_ev_rev, "p_fcf": cur_pfcf},
            history=history,
        )
        if block:
            out["valuation_percentiles"] = block
        missing.extend(pct_missing)
    else:
        missing.append("valuation_percentiles")

    # --- price-based risk ---------------------------------------------------
    if price_history and len(price_history) >= 5:
        vol = annualised_volatility(price_history)
        dd = max_drawdown(price_history)
        if vol is not None:
            out["volatility"] = vol
        if dd is not None:
            out["max_drawdown"] = dd
    else:
        missing.append("price_history")

    return out, missing
