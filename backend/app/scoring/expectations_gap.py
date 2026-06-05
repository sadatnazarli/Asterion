"""Expectations Gap — how much the price depends on future growth beating reality.

M10: fed REAL reverse-DCF implied growth and a blended historical growth
(revenue YoY + revenue CAGR + FCF growth) from app.scoring.real_inputs. Higher =
the market expects a lot to go right.

Backward compatible: with only the legacy keys the formula equals the pre-M10
base (50 + gap*250), so existing tests still pin it. Real richer keys (pe_ratio,
fcf_margin_trend) add small transparent premium terms.
"""
from typing import Dict, Any


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def calculate_expectations_gap(inputs: Dict[str, Any]) -> Dict[str, Any]:
    req = ["implied_growth", "historical_growth_ttm"]
    used, missing = {}, []
    for r in req:
        if inputs.get(r) is not None:
            used[r] = inputs[r]
        else:
            missing.append(r)

    if len(missing) == len(req):
        return {
            "score": 50.0, "confidence": 0.0, "inputs_used": used,
            "missing_inputs": missing, "explanation": "Insufficient data for expectations gap.",
            "failure_modes": ["Missing all required inputs"],
        }

    confidence = 1.0 - (len(missing) / len(req))
    implied = used.get("implied_growth", 0.1)
    historical = used.get("historical_growth_ttm", 0.1)
    gap = implied - historical
    score = 50.0 + (gap * 250.0)  # legacy base

    extras = []
    pe = inputs.get("pe_ratio")
    if pe is not None and pe > 0:
        used["pe_ratio"] = pe
        if pe > 25:
            score += min(15.0, (pe - 25) * 0.3)  # rich multiple => more demanded
            extras.append(f"PE {pe:.0f}")
    fm_tr = inputs.get("fcf_margin_trend")
    if fm_tr is not None:
        used["fcf_margin_trend"] = fm_tr
        if fm_tr < 0:
            score += 5  # demanding growth while margins slip
            extras.append("FCF margin slipping")

    score = _clamp(score)
    expl = f"Implied growth {implied:+.1%} vs historical {historical:+.1%}"
    if extras:
        expl += " + " + ", ".join(extras)
    expl += f". Score: {score:.1f}"
    return {
        "score": score, "confidence": confidence, "inputs_used": used,
        "missing_inputs": missing, "explanation": expl, "failure_modes": [],
    }
