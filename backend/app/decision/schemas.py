from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PolicyClassification(str, Enum):
    strong_company_watchlist = "strong_company_watchlist"
    quality_compounder_candidate = "quality_compounder_candidate"
    improving_business_candidate = "improving_business_candidate"
    wait_for_valuation_data = "wait_for_valuation_data"
    risk_review_required = "risk_review_required"
    speculative_only = "speculative_only"
    avoid_due_to_red_flags = "avoid_due_to_red_flags"
    insufficient_data = "insufficient_data"
    valuation_risk_watchlist = "valuation_risk_watchlist"
    wait_for_better_price = "wait_for_better_price"

class ScorecardOutput(BaseModel):
    classification: PolicyClassification
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    red_flags: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    advanced_scores: Dict[str, Any] = Field(default_factory=dict)
    thesis_invalidation_triggers: List[str] = Field(default_factory=list)
    monitor_next: List[str] = Field(default_factory=list)
    m4_memo_status: str = "Unknown"
    hallucination_audit: str = "Not Available"
