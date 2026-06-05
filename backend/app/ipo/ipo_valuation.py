"""IPO valuation (Phase 4) + reverse-DCF / scenario model (Phase 5). Pure, no I/O.

Computes only what the verified inputs allow. Hard guards:
- No share count  -> no market cap / EV / multiples (returns ``can_value=False``).
- FCF cannot be confirmed positive -> we DO NOT run a normal reverse DCF. We fall
  back to a revenue-multiple / path-to-FCF scenario model, labeled speculative.

Every metric is deterministic from :class:`FilingFacts`. Nothing is invented;
absent inputs land in ``missing``.
"""
from __future__ import annotations

from app.ipo.schemas import FilingFacts, ValuationResult

# Public comps (Phase 4). Reference EV/Sales are coarse public-market anchors for
# *context only* — flagged as approximate; live multiples need the market provider.
_COMPS: list[dict] = [
    {"ticker": "TSLA", "quality": "weak", "ev_sales_ref": 9.0,
     "note": "Elon/governance & hype reference, not a business comp."},
    {"ticker": "LMT", "quality": "partial", "ev_sales_ref": 2.0, "note": "Defense/aerospace prime."},
    {"ticker": "NOC", "quality": "partial", "ev_sales_ref": 2.2, "note": "Defense/aerospace prime."},
    {"ticker": "RTX", "quality": "partial", "ev_sales_ref": 2.5, "note": "Defense/aerospace prime."},
    {"ticker": "RKLB", "quality": "strong", "ev_sales_ref": 30.0, "note": "Closest pure-play launch/space."},
    {"ticker": "ASTS", "quality": "partial", "ev_sales_ref": 120.0, "note": "Sat-to-phone, pre-revenue-ish."},
    {"ticker": "IRDM", "quality": "partial", "ev_sales_ref": 5.0, "note": "Satellite connectivity."},
    {"ticker": "NVDA", "quality": "weak", "ev_sales_ref": 25.0, "note": "Mega-cap growth valuation context only."},
    {"ticker": "AMZN", "quality": "weak", "ev_sales_ref": 3.5, "note": "Infra/capex-heavy context only."},
    {"ticker": "GOOG", "quality": "weak", "ev_sales_ref": 6.5, "note": "Mega-cap context only."},
]

# Scenario assumptions (Phase 5). Transparent, editable, labeled speculative.
_HORIZON_Y = 5
_DISCOUNT_MID = 0.12
_SCENARIOS = [
    {"name": "bear", "revenue_cagr": 0.15, "target_fcf_margin": 0.08, "terminal_fcf_multiple": 18.0},
    {"name": "base", "revenue_cagr": 0.30, "target_fcf_margin": 0.15, "terminal_fcf_multiple": 25.0},
    {"name": "bull", "revenue_cagr": 0.45, "target_fcf_margin": 0.22, "terminal_fcf_multiple": 32.0},
]


def _ev_sales_quality_note(ev_sales: float) -> str:
    strong = [c["ev_sales_ref"] for c in _COMPS if c["quality"] == "strong"]
    hi = max([c["ev_sales_ref"] for c in _COMPS])
    if not strong:
        return "No strong comp."
    if ev_sales > hi:
        return f"EV/Sales {ev_sales:.0f}x exceeds every public comp anchor (max ~{hi:.0f}x)."
    ratio = ev_sales / strong[0]
    return f"EV/Sales {ev_sales:.0f}x is ~{ratio:.1f}x the closest pure-play comp (RKLB ~{strong[0]:.0f}x)."


def build_valuation(facts: FilingFacts) -> ValuationResult:
    price = facts.num("ipo_price_per_share")
    shares_pre = facts.num("total_shares_pre_offering")
    shares_offered = facts.num("shares_offered")
    revenue = facts.num("revenue_fy2025")
    op_loss = facts.num("loss_from_operations_fy2025")  # negative number
    cash = facts.num("cash_and_equivalents")

    res = ValuationResult(can_value=False)

    # Guard: market cap needs price AND a share count.
    if price is None or shares_pre is None:
        res.method = "none"
        if price is None:
            res.missing.append("ipo_price_per_share")
        if shares_pre is None:
            res.missing.append("total_shares_pre_offering")
        res.notes.append("Cannot compute valuation: missing IPO price and/or share count. "
                         "No market cap, EV, or multiples produced.")
        return res

    res.can_value = True
    shares_post = shares_pre + (shares_offered or 0.0)
    market_cap_m = price * shares_post / 1e6  # price*shares is $; report in $millions
    res.metrics["shares_post_offering"] = shares_post
    res.metrics["implied_market_cap_musd"] = market_cap_m

    # Enterprise value (subtract cash; debt not separately parsed -> partial).
    if cash is not None:
        res.metrics["enterprise_value_musd"] = market_cap_m - cash
        res.notes.append("EV = market cap - cash. Debt not separately parsed; EV is a partial "
                         "(net-cash-only) approximation.")
    else:
        res.metrics["enterprise_value_musd"] = None
        res.missing.append("total_debt")

    ev = res.metrics.get("enterprise_value_musd")
    if revenue:
        res.metrics["price_to_sales"] = market_cap_m / revenue
        res.metrics["ev_to_revenue"] = (ev / revenue) if ev is not None else None
        if op_loss is not None:
            res.metrics["operating_margin"] = op_loss / revenue
    else:
        res.missing.append("revenue_fy2025")

    # Dilution from the offering.
    if shares_offered:
        res.metrics["offering_dilution_pct"] = shares_offered / shares_post

    # Net margin needs a GAAP net loss line, which we don't parse cleanly.
    res.metrics["net_margin"] = None
    res.missing.append("net_income_or_loss")

    # FCF: needs OCF and capex totals. Not reliably parsed -> cannot confirm sign.
    ocf = facts.num("operating_cash_flow_fy2025")
    capex = facts.num("capex_fy2025")
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)
        res.metrics["fcf_musd"] = fcf
        res.metrics["fcf_margin"] = (fcf / revenue) if revenue else None
        res.fcf_positive = fcf > 0
    else:
        res.fcf_positive = None
        for k, v in (("operating_cash_flow_fy2025", ocf), ("capex_fy2025", capex)):
            if v is None:
                res.missing.append(k)
        res.notes.append("Free cash flow cannot be computed (OCF and/or total capex not parsed). "
                         "Operating income is negative; treating FCF as unconfirmed.")

    # Comps (context, labeled approximate).
    ps = res.metrics.get("ev_to_revenue") or res.metrics.get("price_to_sales")
    res.comps = [
        {**c, "ev_sales_ref_quality": "approximate_reference_verify_live"} for c in _COMPS
    ]
    if ps:
        res.notes.append(_ev_sales_quality_note(ps))

    # Phase 5: FCF not positive (or unconfirmed) -> scenario model, not reverse DCF.
    if res.fcf_positive and revenue:
        res.method = "reverse_dcf_eligible"
        res.notes.append("FCF positive: a reverse DCF would be appropriate (run separately).")
    elif revenue:
        res.method = "scenario"
        res.scenarios = _scenario_model(revenue, ev or market_cap_m, cash or 0.0)
        res.notes.append("FCF negative/unconfirmed -> SPECULATIVE path-to-FCF scenario model used "
                         "instead of a normal reverse DCF.")
    else:
        res.method = "none"

    return res


def _scenario_model(revenue_m: float, ipo_ev_m: float, cash_m: float) -> list[dict]:
    """Path-to-FCF scenarios. SPECULATIVE — project revenue, apply target FCF margin
    and a terminal FCF multiple, discount back, compare to the IPO EV."""
    out: list[dict] = []
    for sc in _SCENARIOS:
        cagr = sc["revenue_cagr"]
        fcf_margin = sc["target_fcf_margin"]
        mult = sc["terminal_fcf_multiple"]
        fut_rev = revenue_m * (1 + cagr) ** _HORIZON_Y
        fut_fcf = fut_rev * fcf_margin
        fut_ev = fut_fcf * mult
        pv_ev = fut_ev / (1 + _DISCOUNT_MID) ** _HORIZON_Y
        out.append({
            "scenario": sc["name"],
            "horizon_years": _HORIZON_Y,
            "revenue_cagr": cagr,
            "target_fcf_margin": fcf_margin,
            "terminal_fcf_multiple": mult,
            "discount_rate": _DISCOUNT_MID,
            "projected_revenue_musd": round(fut_rev, 0),
            "projected_fcf_musd": round(fut_fcf, 0),
            "pv_enterprise_value_musd": round(pv_ev, 0),
            "implied_equity_value_musd": round(pv_ev + cash_m, 0),
            "gap_vs_ipo_ev_pct": round((pv_ev / ipo_ev_m - 1.0), 3) if ipo_ev_m else None,
            "label": "speculative",
        })
    return out
