from typing import Dict, List, Any
from app.decision.schemas import PolicyClassification, ScorecardOutput

def evaluate_policy(
    ratios: Dict[str, float],
    advanced_scores: Dict[str, Any],
    missing_data: List[str],
    hallucination_failed: bool = False,
    m4_memo_status: str = "Unavailable"
) -> ScorecardOutput:
    """
    A hardcoded deterministic rule-engine that returns a classification based on metrics.
    No LLMs used.
    """
    thesis_triggers = []
    monitor_list = []
    
    if hallucination_failed:
        return ScorecardOutput(
            classification=PolicyClassification.insufficient_data,
            confidence=0.0,
            reason="Hallucination check failed, data is unreliable.",
            metrics=ratios,
            red_flags=["Hallucination detected"],
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=["Data ingestion error or model failure"],
            monitor_next=["Audit system logs", "Re-run RAG pipeline"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="FAILED"
        )

    if missing_data and len(missing_data) > 5:
        return ScorecardOutput(
            classification=PolicyClassification.insufficient_data,
            confidence=0.0,
            reason=f"Too many missing data points: {', '.join(missing_data)}",
            metrics=ratios,
            red_flags=[],
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=[],
            monitor_next=["Wait for next SEC filing"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED" if not hallucination_failed else "FAILED"
        )

    red_flags = []
    
    pe_ratio = ratios.get("pe_ratio")
    debt_to_equity = ratios.get("debt_to_equity")
    roa = ratios.get("roa")
    roe = ratios.get("roe")
    gross_margin = ratios.get("gross_margin")
    fcf_margin = ratios.get("fcf_margin")
    current_ratio = ratios.get("current_ratio")
    
    if debt_to_equity is not None and debt_to_equity > 2.0:
        red_flags.append(f"High debt to equity ratio: {debt_to_equity}")
        thesis_triggers.append("Debt covenant breach or liquidity crisis")
    if roa is not None and roa < 0:
        red_flags.append(f"Negative ROA: {roa}")
    
    op_leverage_score = advanced_scores.get("operating_leverage_convexity", {}).get("score", 0)
    if not op_leverage_score:
        op_leverage_score = advanced_scores.get("Operating Leverage Convexity Score", {}).get("score", 0)
        
    reflex_risk = advanced_scores.get("reflexivity_risk", {}).get("score", 0)
    if not reflex_risk:
        reflex_risk = advanced_scores.get("Reflexivity Risk Score", {}).get("score", 0)
        
    expectations_gap = advanced_scores.get("expectations_gap", {}).get("score", 0)

    if reflex_risk > 70:
        red_flags.append("High Reflexivity Risk (SBC/Debt dependency)")
        thesis_triggers.append("Stock price drop triggering dilution spiral")

    if len(red_flags) >= 2:
        return ScorecardOutput(
            classification=PolicyClassification.avoid_due_to_red_flags,
            confidence=0.8,
            reason="Multiple structural red flags detected.",
            metrics=ratios,
            red_flags=red_flags,
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=thesis_triggers,
            monitor_next=["Debt levels", "SBC burn"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED"
        )

    if "pe_ratio" in missing_data or pe_ratio is None:
        reason = "Asterion cannot determine attractiveness of current price yet due to missing valuation data."
        if gross_margin and gross_margin > 0.7 and fcf_margin and fcf_margin > 0.15:
            reason += " However, underlying business appears to be a Quality Compounder."
            
        return ScorecardOutput(
            classification=PolicyClassification.wait_for_valuation_data,
            confidence=0.9,
            reason=reason,
            metrics=ratios,
            red_flags=red_flags,
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=thesis_triggers + ["Multiple compression if growth slows"],
            monitor_next=["Price action", "Next earnings multiple"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED"
        )

    is_quality = (gross_margin and gross_margin > 0.7 and fcf_margin and fcf_margin > 0.15 and op_leverage_score > 70)

    if pe_ratio > 40 and expectations_gap > 70:
        return ScorecardOutput(
            classification=PolicyClassification.valuation_risk_watchlist,
            confidence=0.8,
            reason="Valuation multiples are highly stretched alongside a large expectations gap. Priced for perfection.",
            metrics=ratios,
            red_flags=red_flags,
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=thesis_triggers + ["Growth deceleration", "Multiple contraction"],
            monitor_next=["Revenue growth", "Valuation multiples"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED"
        )

    if pe_ratio > 25 or expectations_gap > 50:
        return ScorecardOutput(
            classification=PolicyClassification.wait_for_better_price,
            confidence=0.75,
            reason="Business is solid but current valuation multiples and expectations gap suggest limited margin of safety.",
            metrics=ratios,
            red_flags=red_flags,
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=thesis_triggers + ["Multiple compression"],
            monitor_next=["Price action", "Entry multiples"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED"
        )

    if is_quality:
        return ScorecardOutput(
            classification=PolicyClassification.quality_compounder_candidate,
            confidence=0.85,
            reason="Strong margins, operating leverage convexity, and reasonable valuation multiples with low expectations gap.",
            metrics=ratios,
            red_flags=red_flags,
            missing_data=missing_data,
            advanced_scores=advanced_scores,
            thesis_invalidation_triggers=thesis_triggers + ["Margin degradation", "Loss of pricing power"],
            monitor_next=["Gross margin stability", "FCF conversion"],
            m4_memo_status=m4_memo_status,
            hallucination_audit="PASSED"
        )

    return ScorecardOutput(
        classification=PolicyClassification.risk_review_required,
        confidence=0.6,
        reason="Mixed signals, requires further risk review.",
        metrics=ratios,
        red_flags=red_flags,
        missing_data=missing_data,
        advanced_scores=advanced_scores,
        thesis_invalidation_triggers=thesis_triggers,
        monitor_next=["General execution"],
        m4_memo_status=m4_memo_status,
        hallucination_audit="PASSED"
    )
