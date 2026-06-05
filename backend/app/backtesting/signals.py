"""Signal extraction + bucketing for evaluation.

Turns a ScoreSnapshot into the boolean/categorical buckets the evaluation step
groups on (high vs low expectations gap, high vs low valuation risk, etc.).
Thresholds mirror the policy engine and calibration bands so the backtest asks
the same questions the live system asks.
"""
from __future__ import annotations

from app.scoring.calibration import band_for

from .schemas import ScoreSnapshot

# Bucket thresholds (0–100 score space). "high" = elevated/high band, i.e. ≥ 50.
HIGH_BAND_MIN = 50.0


def is_high(score: float | None) -> bool | None:
    """True if score sits in the elevated/high half, None if unknown."""
    if score is None:
        return None
    return band_for(score) in ("elevated", "high")


def bucket(snapshot: ScoreSnapshot) -> dict[str, bool | None]:
    """Categorical flags used by evaluation grouping."""
    return {
        "high_valuation_risk": snapshot.high_valuation_risk,
        "high_expectations_gap": is_high(snapshot.expectations_gap),
        "high_thesis_fragility": is_high(snapshot.thesis_fragility),
        "high_operating_leverage": is_high(snapshot.operating_leverage_convexity),
        "high_reflexivity_risk": is_high(snapshot.reflexivity_risk),
    }
