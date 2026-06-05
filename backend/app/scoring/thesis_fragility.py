"""Thesis Fragility — how easily the thesis breaks if assumptions disappoint.

M10: now a transparent weighted blend of REAL sub-signals built by
app.scoring.real_inputs:
  - reverse-DCF sensitivity spread (primary)
  - valuation multiple level (PE)
  - implied-vs-historical growth dependency
  - margin dependency (low / declining FCF margin)
  - dilution (SBC / share growth)
  - leverage & liquidity
  - recent volatility / drawdown

Higher = more fragile. Backward compatible: when called with ONLY
``dcf_sensitivity_impact`` (no richer keys) it returns the legacy
``impact*100`` so existing tests still pin it.
"""
from typing import Dict, Any


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# Sub-signal weights (sum ≈ 1.0). Documented, deterministic.
_WEIGHTS = {
    "sensitivity": 0.30,
    "valuation": 0.15,
    "growth_dependency": 0.15,
    "margin": 0.12,
    "dilution": 0.10,
    "leverage": 0.10,
    "price_risk": 0.08,
}

_RICH_KEYS = (
    "pe_ratio", "implied_growth", "historical_growth_ttm", "fcf_margin",
    "fcf_margin_trend", "sbc_to_revenue", "shares_change", "debt_to_equity",
    "current_ratio", "volatility", "max_drawdown",
)


def calculate_thesis_fragility(inputs: Dict[str, Any]) -> Dict[str, Any]:
    req = ["dcf_sensitivity_impact"]
    used, missing = {}, []
    for r in req:
        if inputs.get(r) is not None:
            used[r] = inputs[r]
        else:
            missing.append(r)

    has_rich = any(inputs.get(k) is not None for k in _RICH_KEYS)

    # Legacy path: only the sensitivity impact, no richer data → impact*100.
    if not has_rich:
        if missing:
            return {
                "score": 50.0, "confidence": 0.0, "inputs_used": used,
                "missing_inputs": missing, "explanation": "Insufficient data for thesis fragility.",
                "failure_modes": ["Missing all required inputs"],
            }
        impact = used["dcf_sensitivity_impact"]
        score = max(0.0, min(100.0, impact * 100.0))
        return {
            "score": score, "confidence": 1.0, "inputs_used": used,
            "missing_inputs": [], "explanation": f"Thesis fragility from DCF sensitivity. Score: {score:.1f}",
            "failure_modes": [],
        }

    # Rich path: weighted blend of available 0–1 sub-signals (reweighted by coverage).
    signals: dict[str, float] = {}

    sens = inputs.get("dcf_sensitivity_impact")
    if sens is not None:
        signals["sensitivity"] = _clamp01(sens)
        used["dcf_sensitivity_impact"] = sens

    pe = inputs.get("pe_ratio")
    if pe is not None and pe > 0:
        signals["valuation"] = _clamp01(pe / 60.0)
        used["pe_ratio"] = pe

    ig, hg = inputs.get("implied_growth"), inputs.get("historical_growth_ttm")
    if ig is not None and hg is not None:
        signals["growth_dependency"] = _clamp01((ig - hg) / 0.30)
        used["implied_growth"] = ig
        used["historical_growth_ttm"] = hg

    fm = inputs.get("fcf_margin")
    fm_tr = inputs.get("fcf_margin_trend")
    if fm is not None or fm_tr is not None:
        m = 0.0
        if fm is not None:
            m = max(m, _clamp01((0.15 - fm) / 0.15))  # low FCF margin ⇒ fragile
            used["fcf_margin"] = fm
        if fm_tr is not None and fm_tr < 0:
            m = max(m, 0.6)
            used["fcf_margin_trend"] = fm_tr
        signals["margin"] = m

    sbc = inputs.get("sbc_to_revenue")
    sc = inputs.get("shares_change")
    if sbc is not None or sc is not None:
        d = 0.0
        if sbc is not None:
            d = max(d, _clamp01(sbc / 0.15))
            used["sbc_to_revenue"] = sbc
        if sc is not None and sc > 0:
            d = max(d, _clamp01(sc / 0.10))
            used["shares_change"] = sc
        signals["dilution"] = d

    dte = inputs.get("debt_to_equity")
    cr = inputs.get("current_ratio")
    if dte is not None or cr is not None:
        lv = 0.0
        if dte is not None:
            lv = max(lv, _clamp01(dte / 2.0))
            used["debt_to_equity"] = dte
        if cr is not None and cr < 1.0:
            lv = max(lv, _clamp01((1.0 - cr)))
            used["current_ratio"] = cr
        signals["leverage"] = lv

    vol = inputs.get("volatility")
    dd = inputs.get("max_drawdown")
    if vol is not None or dd is not None:
        pr = 0.0
        if vol is not None:
            pr = max(pr, _clamp01(vol / 0.80))
            used["volatility"] = vol
        if dd is not None:
            pr = max(pr, _clamp01(abs(dd) / 0.50))
            used["max_drawdown"] = dd
        signals["price_risk"] = pr

    if not signals:
        return {
            "score": 50.0, "confidence": 0.0, "inputs_used": used,
            "missing_inputs": ["dcf_sensitivity_impact"], "explanation": "Insufficient data for thesis fragility.",
            "failure_modes": ["No usable sub-signals"],
        }

    total_w = sum(_WEIGHTS[k] for k in signals)
    blended = sum(_WEIGHTS[k] * v for k, v in signals.items()) / total_w
    score = max(0.0, min(100.0, blended * 100.0))
    confidence = round(total_w / sum(_WEIGHTS.values()), 4)  # fraction of weight covered
    if "dcf_sensitivity_impact" not in used:
        missing = ["dcf_sensitivity_impact"]
    else:
        missing = []

    top = sorted(signals.items(), key=lambda kv: _WEIGHTS[kv[0]] * kv[1], reverse=True)[:3]
    expl = "Fragility blend of " + ", ".join(f"{k} {v:.2f}" for k, v in top)
    expl += f". Score: {score:.1f}"
    return {
        "score": score, "confidence": confidence, "inputs_used": used,
        "missing_inputs": missing, "explanation": expl, "failure_modes": [],
    }
