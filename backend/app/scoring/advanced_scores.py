"""Advanced 0–100 score functions.

M10: these now accept RICH per-ticker inputs (margin/revenue trends, dilution,
volatility, drawdown, reverse-DCF sensitivity) built by ``app.scoring.real_inputs``.
They remain BACKWARD COMPATIBLE: when called with only the legacy keys the output
is identical to the pre-M10 formula, so existing unit tests still pin the base.
Richer keys add transparent adjustment terms — no hidden/fancy math, every term
is documented inline. Missing data degrades confidence; nothing is fabricated.
"""
from typing import Dict, Any, List


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _num(x) -> float | None:
    """Coerce to float; None for missing or non-numeric (e.g. legacy 'expanding')."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _build_result(score: float, confidence: float, inputs_used: Dict[str, Any], missing_inputs: List[str], explanation: str, failure_modes: List[str]) -> Dict[str, Any]:
    return {
        "score": _clamp(score),
        "confidence": max(0.0, min(1.0, confidence)),
        "inputs_used": inputs_used,
        "missing_inputs": missing_inputs,
        "explanation": explanation,
        "failure_modes": failure_modes
    }


def _collect(inputs: Dict[str, Any], required: List[str]) -> tuple[dict, list]:
    used, missing = {}, []
    for r in required:
        if inputs.get(r) is not None:
            used[r] = inputs[r]
        else:
            missing.append(r)
    return used, missing


def calculate_operating_leverage_convexity(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Higher = revenue growth converts into stronger operating/cash expansion.

    Base (legacy): 50 + gross_margin*100*revenue_growth.
    Real adjustments (when supplied): operating-leverage ratio (op-income growth
    vs revenue growth), operating-margin trend, FCF-margin trend.
    """
    req = ["gross_margin", "revenue_growth_yoy"]
    used, missing = _collect(inputs, req)
    if len(missing) == len(req):
        return _build_result(50.0, 0.0, used, missing, "Insufficient data for operating leverage.", ["Missing all required inputs"])

    confidence = 1.0 - (len(missing) / len(req))
    gm = used.get("gross_margin", 0.5)
    rev_growth = used.get("revenue_growth_yoy", 0.0)
    score = 50 + (gm * 100 * rev_growth)

    extras = []
    olr = _num(inputs.get("operating_leverage_ratio"))
    if olr is not None:
        used["operating_leverage_ratio"] = olr
        if olr > 1:
            score += min(15.0, (olr - 1) * 15)
            extras.append(f"op-leverage {olr:.2f}× (convex)")
        elif olr > 0:
            score -= min(10.0, (1 - olr) * 10)
            extras.append(f"op-leverage {olr:.2f}× (deleveraging)")
    om_tr = _num(inputs.get("operating_margin_trend"))
    if om_tr is not None:
        used["operating_margin_trend"] = om_tr
        score += 8 if om_tr > 0 else -8
        extras.append("op-margin " + ("rising" if om_tr > 0 else "falling"))
    fm_tr = _num(inputs.get("fcf_margin_trend"))
    if fm_tr is not None:
        used["fcf_margin_trend"] = fm_tr
        score += 5 if fm_tr > 0 else -5

    expl = f"Operating leverage from GM×growth"
    if extras:
        expl += " + " + ", ".join(extras)
    expl += f". Score: {_clamp(score):.1f}"
    return _build_result(score, confidence, used, missing, expl, [])


def calculate_reflexivity_risk(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Financial Reflexivity / Market-Structure Risk (MVP).

    NOTE: this measures balance-sheet + dilution + price fragility, NOT true
    price-feedback reflexivity. Renamed accordingly. Higher = a price drop is
    more likely to feed on itself (refinancing, dilution, volatility).

    Base (legacy): debt_to_equity*20 + (2 − min(current_ratio,2))*20.
    Real adjustments: SBC/revenue, share dilution, volatility, drawdown.
    """
    req = ["current_ratio", "debt_to_equity"]
    used, missing = _collect(inputs, req)
    if len(missing) == len(req):
        return _build_result(50.0, 0.0, used, missing, "Insufficient data for financial reflexivity.", ["Missing all required inputs"])

    confidence = 1.0 - (len(missing) / len(req))
    cr = used.get("current_ratio", 1.5)
    dte = used.get("debt_to_equity", 1.0)
    risk = (dte * 20) + ((2.0 - min(cr, 2.0)) * 20)

    extras = []
    sbc = _num(inputs.get("sbc_to_revenue"))
    if sbc is not None:
        used["sbc_to_revenue"] = sbc
        risk += min(15.0, sbc * 100)
        if sbc > 0.05:
            extras.append(f"SBC {sbc:.1%} of revenue")
    dil = _num(inputs.get("shares_change"))
    if dil is not None:
        used["shares_change"] = dil
        if dil > 0:
            risk += min(10.0, dil * 50)
            extras.append(f"dilution +{dil:.1%}")
    vol = _num(inputs.get("volatility"))
    if vol is not None:
        used["volatility"] = vol
        if vol > 0.4:
            risk += min(10.0, (vol - 0.4) * 25)
            extras.append(f"vol {vol:.0%}")
    dd = _num(inputs.get("max_drawdown"))
    if dd is not None:
        used["max_drawdown"] = dd
        if dd < -0.25:
            risk += min(10.0, (abs(dd) - 0.25) * 40)
            extras.append(f"drawdown {dd:.0%}")

    expl = "Financial reflexivity from leverage/liquidity"
    if extras:
        expl += " + " + ", ".join(extras)
    expl += f" (MVP — not true reflexivity). Risk: {_clamp(risk):.1f}"
    return _build_result(risk, confidence, used, missing, expl, [])


def calculate_misunderstood_change(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Higher = company invests for the future while sentiment lags.

    capex_growth is now REAL (from SEC facts). sentiment_shift requires an NLP
    feed that is not yet ingested → typically missing, lowering confidence. Marked
    weak until sentiment lands.
    """
    req = ["sentiment_shift", "capex_growth"]
    used, missing = _collect(inputs, req)
    if len(missing) == len(req):
        return _build_result(50.0, 0.0, used, missing, "Insufficient data for misunderstood change.", ["Missing all required inputs"])

    confidence = 1.0 - (len(missing) / len(req))
    sentiment = used.get("sentiment_shift", 0.5)
    capex = used.get("capex_growth", 0.0)
    score = 50 + (capex * 100) - (sentiment * 50)
    note = "" if "sentiment_shift" in used else " (sentiment feed missing — weak)"
    return _build_result(score, confidence, used, missing, f"Misunderstood change: capex {capex:+.1%}{note}. Score: {_clamp(score):.1f}", [])


def calculate_perception_shift(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Higher = improving analyst perception. Requires analyst/surprise feeds
    not yet ingested → placeholder; returns low confidence when missing."""
    req = ["analyst_revisions", "earnings_surprise"]
    used, missing = _collect(inputs, req)
    if len(missing) == len(req):
        return _build_result(50.0, 0.0, used, missing, "Insufficient data for perception shift.", ["Missing all required inputs"])
    confidence = 1.0 - (len(missing) / len(req))
    rev = used.get("analyst_revisions", 0.5)
    surprise = used.get("earnings_surprise", 0.0)
    score = 50 + (rev * 50) + (surprise * 100)
    return _build_result(score, confidence, used, missing, f"Perception shift score: {_clamp(score):.1f}", [])


def calculate_narrative_entropy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Higher = management narrative is scattering. Requires transcript NLP not
    yet computed → placeholder."""
    req = ["management_tone_variance", "topic_dispersion"]
    used, missing = _collect(inputs, req)
    if len(missing) == len(req):
        return _build_result(50.0, 0.0, used, missing, "Insufficient data for narrative entropy.", ["Missing all required inputs"])
    confidence = 1.0 - (len(missing) / len(req))
    tone_var = used.get("management_tone_variance", 0.0)
    topic_disp = used.get("topic_dispersion", 0.0)
    score = (tone_var * 50) + (topic_disp * 50)
    return _build_result(score, confidence, used, missing, f"Narrative entropy score: {_clamp(score):.1f}", [])
