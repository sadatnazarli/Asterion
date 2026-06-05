"""Score calibration — interpretation bands and direction for every 0–100 score.

Deterministic, no LLM, no DB. Maps a raw 0–100 score to:
  - a positional band  (low / moderate / elevated / high)
  - a *direction*       (higher_is_better | higher_is_risk | neutral)
  - a plain-English interpretation that respects the direction

The positional band is the same for every score (0–25 low … 75–100 high), but
the *meaning* of a high band flips with direction: a high Operating-Leverage
score is good; a high Reflexivity-Risk score is bad. The UI must read
``direction`` to colour the score correctly.

Bands (positional, identical for all scores):
    0–25   low
    25–50  moderate
    50–75  elevated
    75–100 high
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["higher_is_better", "higher_is_risk", "neutral"]
BandLabel = Literal["low", "moderate", "elevated", "high"]

# Positional band edges. Lower-inclusive, upper-exclusive except the last.
BAND_EDGES: tuple[tuple[float, float, BandLabel], ...] = (
    (0.0, 25.0, "low"),
    (25.0, 50.0, "moderate"),
    (50.0, 75.0, "elevated"),
    (75.0, 100.01, "high"),
)


@dataclass(frozen=True, slots=True)
class CalibrationSpec:
    """How to interpret one 0–100 score."""

    key: str
    name: str
    direction: Direction
    # Plain-English meaning of each positional band, written for a beginner.
    band_explanations: dict[BandLabel, str]
    # Maturity flag — honest about which scores are production vs placeholder.
    maturity: Literal["production", "mvp", "placeholder"] = "mvp"
    # One-line note on what the score is and its biggest caveat.
    note: str = ""


def band_for(score: float) -> BandLabel:
    """Return the positional band label for a 0–100 score (clamped)."""
    s = max(0.0, min(100.0, float(score)))
    for lo, hi, label in BAND_EDGES:
        if lo <= s < hi:
            return label
    return "high"  # s == 100.0 falls through


def is_concerning(score: float, direction: Direction) -> bool:
    """True when this score, given its direction, points to *risk* (elevated+)."""
    band = band_for(score)
    high_side = band in ("elevated", "high")
    if direction == "higher_is_risk":
        return high_side
    if direction == "higher_is_better":
        # Risk is the LOW side for a higher-is-better score.
        return band in ("low", "moderate")
    return False  # neutral scores never auto-flag


# ---------------------------------------------------------------------------
# Calibration registry — one entry per implemented 0–100 score.
# ---------------------------------------------------------------------------

CALIBRATION: dict[str, CalibrationSpec] = {
    "operating_leverage_convexity": CalibrationSpec(
        key="operating_leverage_convexity",
        name="Operating Leverage Convexity",
        direction="higher_is_better",
        maturity="mvp",
        note=(
            "score = 50 + gross_margin*100*revenue_growth. Naive; rewards "
            "high-margin growers, but unbounded and untuned. Needs calibration."
        ),
        band_explanations={
            "low": "Little operating leverage — profit barely scales as revenue grows.",
            "moderate": "Some operating leverage, but the upside is modest.",
            "elevated": "Good operating leverage — extra revenue should drop to profit.",
            "high": "Strong convex upside — high margins plus growth compound earnings fast.",
        },
    ),
    "reflexivity_risk": CalibrationSpec(
        key="reflexivity_risk",
        name="Financial Reflexivity / Market-Structure Risk",
        direction="higher_is_risk",
        maturity="mvp",
        note=(
            "RENAMED (M10): measures leverage/liquidity + SBC dilution + volatility/"
            "drawdown, NOT true price-feedback reflexivity. Now fed real per-ticker "
            "inputs. base = dte*20 + (2 - min(current_ratio,2))*20 + real risk terms."
        ),
        band_explanations={
            "low": "Balance sheet is sturdy — little risk of a self-reinforcing decline.",
            "moderate": "Some leverage or thin liquidity, but manageable.",
            "elevated": "Leverage/liquidity could amplify a downturn.",
            "high": "Fragile balance sheet — a price drop could feed on itself (dilution/refinancing).",
        },
    ),
    "expectations_gap": CalibrationSpec(
        key="expectations_gap",
        name="Expectations Gap",
        direction="higher_is_risk",
        maturity="mvp",
        note=(
            "M10: fed REAL reverse-DCF implied growth + blended historical growth "
            "(revenue YoY/CAGR + FCF growth). base = 50 + (implied - historical)*250 "
            "+ valuation premium. Still uses a fixed 10% WACC — see docs/25."
        ),
        band_explanations={
            "low": "The price asks for less growth than the company already delivers — low bar.",
            "moderate": "Expectations roughly match the track record.",
            "elevated": "The market expects more growth than history — a stretch.",
            "high": "Priced for perfection — the market demands far more growth than delivered.",
        },
    ),
    "thesis_fragility": CalibrationSpec(
        key="thesis_fragility",
        name="Thesis Fragility",
        direction="higher_is_risk",
        maturity="mvp",
        note=(
            "M10: now a real weighted blend (DCF-sensitivity spread where FCF "
            "exists + valuation + growth dependency + margin + dilution + leverage "
            "+ price risk). Degrades to low confidence when capex/FCF is absent."
        ),
        band_explanations={
            "low": "Valuation holds up even if assumptions move — robust thesis.",
            "moderate": "Somewhat sensitive to growth/discount assumptions.",
            "elevated": "Valuation swings a lot on small assumption changes.",
            "high": "Fragile — the thesis breaks on small changes to growth or rates.",
        },
    ),
    "misunderstood_change": CalibrationSpec(
        key="misunderstood_change",
        name="Misunderstood Change",
        direction="higher_is_better",
        maturity="placeholder",
        note=(
            "score = 50 + capex_growth*100 - sentiment_shift*50. Needs sentiment "
            "and capex inputs that are not yet fetched from real data. Placeholder."
        ),
        band_explanations={
            "low": "Sentiment already reflects the story — little hidden upside.",
            "moderate": "Mixed signals on whether the market sees the change.",
            "elevated": "The market may be underrating an investment cycle.",
            "high": "Possible misunderstood pivot — investing heavily while sentiment lags.",
        },
    ),
    "perception_shift": CalibrationSpec(
        key="perception_shift",
        name="Perception Shift",
        direction="higher_is_better",
        maturity="placeholder",
        note=(
            "score = 50 + analyst_revisions*50 + earnings_surprise*100. Requires "
            "analyst-revision and surprise feeds not yet ingested. Placeholder."
        ),
        band_explanations={
            "low": "Perception is deteriorating — downgrades or misses.",
            "moderate": "Perception is steady.",
            "elevated": "Perception is improving — upward revisions and beats.",
            "high": "Strong positive re-rating in analyst views and surprises.",
        },
    ),
    "narrative_entropy": CalibrationSpec(
        key="narrative_entropy",
        name="Narrative Entropy",
        direction="higher_is_risk",
        maturity="placeholder",
        note=(
            "score = tone_variance*50 + topic_dispersion*50. Requires NLP features "
            "from transcripts not yet computed. Placeholder."
        ),
        band_explanations={
            "low": "Management story is consistent and focused.",
            "moderate": "Some drift in tone or topics across communications.",
            "elevated": "The narrative is wobbling — mixed messages.",
            "high": "Incoherent narrative — tone and topics scatter, a yellow flag.",
        },
    ),
}


def get_spec(key: str) -> CalibrationSpec | None:
    """Look up a calibration spec by score key."""
    return CALIBRATION.get(key)


def interpret(key: str, score: float | None) -> dict[str, object]:
    """Full interpretation of a score for a given metric key.

    Returns a dict with band, direction, concerning flag, label, and the
    plain-English explanation. When the key is unknown or score is None the
    interpretation is marked ``available=False`` instead of guessing.
    """
    spec = CALIBRATION.get(key)
    if spec is None or score is None:
        return {
            "available": False,
            "key": key,
            "score": score,
            "band": None,
            "direction": spec.direction if spec else "neutral",
            "concerning": False,
            "explanation": "No calibration available for this score.",
            "maturity": spec.maturity if spec else "unknown",
        }
    band = band_for(score)
    return {
        "available": True,
        "key": key,
        "name": spec.name,
        "score": round(float(score), 2),
        "band": band,
        "direction": spec.direction,
        "concerning": is_concerning(score, spec.direction),
        "explanation": spec.band_explanations[band],
        "maturity": spec.maturity,
        "note": spec.note,
    }


def direction_hint(key: str) -> str:
    """Short UI tooltip text: 'High is good' / 'High is risk' / 'Neutral'."""
    spec = CALIBRATION.get(key)
    if spec is None:
        return "Neutral"
    return {
        "higher_is_better": "High is good",
        "higher_is_risk": "High is risk",
        "neutral": "Neutral",
    }[spec.direction]
