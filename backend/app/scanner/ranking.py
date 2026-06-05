"""Deterministic opportunity ranking over the universe.

Pure module — no I/O, no LLM. Given valuation-scorecard dicts (as produced by
``generate_real_scorecard`` / stored in ``reports/*_valuation_scorecard.json``),
it builds a transparent composite *screen score* and ranks the names.

Design rules (mirrors Asterion's contract):
- **No advice.** Output classifications are "screens_well" / "neutral" /
  "screens_poorly" / "insufficient_data" — never buy/sell.
- **Transparent weights.** Every component and weight is a named constant below.
- **Honest about uncertainty.** Low confidence or many missing inputs caps the
  classification at "insufficient_data" and pushes the name down the ranking.
- **Risk is inverted.** Higher reflexivity-risk / thesis-fragility lowers the
  score; they are not rewarded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Composite weights — must sum to 1.0. Documented, deterministic, auditable.
WEIGHTS: dict[str, float] = {
    "value": 0.30,    # expectations_gap: higher => cheaper vs. its own fundamentals
    "quality": 0.25,  # operating_leverage_convexity: higher => stronger operating model
    "safety": 0.30,   # inverse of reflexivity_risk & thesis_fragility
    "change": 0.15,   # misunderstood_change: higher => more positive under-appreciated change
}

# Confidence below this floor => classification is capped at "insufficient_data"
# regardless of the composite, and the name is sorted to the bottom.
_MIN_CONFIDENCE = 0.40

# Composite bucket thresholds (0–100).
_WELL = 60.0
_POOR = 40.0


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _score(adv: dict[str, Any], key: str) -> float | None:
    block = adv.get(key)
    if not isinstance(block, dict):
        return None
    val = block.get("score")
    return float(val) if isinstance(val, (int, float)) else None


def _conf(adv: dict[str, Any], key: str) -> float | None:
    block = adv.get(key)
    if not isinstance(block, dict):
        return None
    val = block.get("confidence")
    return float(val) if isinstance(val, (int, float)) else None


@dataclass
class Opportunity:
    ticker: str
    composite: float | None            # 0–100 screen score, None if uncomputable
    classification: str                # screens_well|neutral|screens_poorly|insufficient_data
    confidence: float                  # 0–1 blended
    components: dict[str, float | None] # value|quality|safety|change (0–100)
    drivers: list[str]                 # short, neutral, evidence-style phrases
    missing: list[str]                 # missing component names
    valuation_classification: str | None  # the underlying scorecard's own label (context)
    evidence: dict[str, str]           # links to scorecard / ticker
    # Cross-sectional calibration (filled by app.scanner.calibration). Absolute
    # values above; these are percentile-ranked vs the ingested universe.
    components_calibrated: dict[str, float | None] | None = None
    percentiles: dict[str, float | None] | None = None
    composite_calibrated: float | None = None
    classification_calibrated: str | None = None
    calibration: str = "absolute"
    # Absolute (pinned) calibration (filled by app.scanner.absolute_calibration).
    # Universe-independent: anchored to a fixed reference, with named bands.
    components_anchored: dict[str, float | None] | None = None
    components_band: dict[str, str | None] | None = None
    composite_anchored: float | None = None
    composite_band: str | None = None
    composite_grade: str | None = None
    absolute_method: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            # Headline screen score = calibrated when available, else absolute.
            "composite": self._round(self.composite_calibrated if self.calibration == "cross_sectional" else self.composite),
            "classification": (
                self.classification_calibrated if self.calibration == "cross_sectional" and self.classification_calibrated
                else self.classification
            ),
            "confidence": round(self.confidence, 2),
            "components": {
                k: self._round(v) for k, v in (
                    (self.components_calibrated or self.components)
                    if self.calibration == "cross_sectional" else self.components
                ).items()
            },
            # Always expose the raw absolute layer for full transparency.
            "composite_absolute": self._round(self.composite),
            "classification_absolute": self.classification,
            "components_absolute": {k: self._round(v) for k, v in self.components.items()},
            "percentiles": (
                None if self.percentiles is None
                else {k: self._round(v) for k, v in self.percentiles.items()}
            ),
            "calibration": self.calibration,
            # Absolute (pinned, universe-independent) layer — always present.
            "composite_anchored": self._round(self.composite_anchored),
            "composite_band": self.composite_band,
            "composite_grade": self.composite_grade,
            "components_anchored": (
                None if self.components_anchored is None
                else {k: self._round(v) for k, v in self.components_anchored.items()}
            ),
            "components_band": self.components_band,
            "absolute_method": self.absolute_method,
            "drivers": self.drivers,
            "missing": self.missing,
            "valuation_classification": self.valuation_classification,
            "evidence": self.evidence,
        }

    @staticmethod
    def _round(v: float | None) -> float | None:
        return None if v is None else round(v, 1)


def build_opportunity(scorecard: dict[str, Any]) -> Opportunity:
    """Build one ranked Opportunity from a valuation scorecard dict."""
    ticker = str(scorecard.get("ticker") or "?").upper()
    adv = scorecard.get("advanced_scores") or {}

    value = _score(adv, "expectations_gap")
    quality = _score(adv, "operating_leverage_convexity")
    reflex = _score(adv, "reflexivity_risk")
    fragility = _score(adv, "thesis_fragility")
    change = _score(adv, "misunderstood_change")

    # Safety = how robust the name looks = inverse of risk signals.
    safety_parts = [100.0 - reflex if reflex is not None else None,
                    100.0 - fragility if fragility is not None else None]
    present_safety = [s for s in safety_parts if s is not None]
    safety = sum(present_safety) / len(present_safety) if present_safety else None

    components: dict[str, float | None] = {
        "value": None if value is None else _clamp(value),
        "quality": None if quality is None else _clamp(quality),
        "safety": None if safety is None else _clamp(safety),
        "change": None if change is None else _clamp(change),
    }

    missing = [k for k, v in components.items() if v is None]

    # Composite = weight-renormalized average over the components we actually have.
    present = {k: v for k, v in components.items() if v is not None}
    if present:
        wsum = sum(WEIGHTS[k] for k in present)
        composite = sum(components[k] * WEIGHTS[k] for k in present) / wsum  # type: ignore[operator]
    else:
        composite = None

    # Confidence: scorecard's own confidence, knocked down for missing components.
    base_conf = scorecard.get("confidence")
    base_conf = float(base_conf) if isinstance(base_conf, (int, float)) else 0.0
    coverage = len(present) / len(components)  # fraction of components available
    confidence = _clamp(base_conf * coverage, 0.0, 1.0)

    # Classification — confidence gate first, then composite buckets. No advice.
    if composite is None or confidence < _MIN_CONFIDENCE:
        classification = "insufficient_data"
    elif composite >= _WELL:
        classification = "screens_well"
    elif composite <= _POOR:
        classification = "screens_poorly"
    else:
        classification = "neutral"

    drivers = _drivers(components)

    evidence = {
        "scorecard": f"/api/tickers/{ticker}/valuation",
        "ticker_page": f"/ticker/{ticker}",
    }

    return Opportunity(
        ticker=ticker,
        composite=composite,
        classification=classification,
        confidence=confidence,
        components=components,
        drivers=drivers,
        missing=missing,
        valuation_classification=scorecard.get("classification"),
        evidence=evidence,
    )


def _drivers(components: dict[str, float | None]) -> list[str]:
    """Short, neutral, evidence-style phrases — what moved the screen, not advice."""
    labels = {
        "value": ("attractive valuation gap", "stretched valuation"),
        "quality": ("strong operating model", "weak operating leverage"),
        "safety": ("robust / low fragility", "elevated risk / fragility"),
        "change": ("positive under-appreciated change", "little positive change"),
    }
    out: list[str] = []
    for key, (hi, lo) in labels.items():
        v = components.get(key)
        if v is None:
            continue
        if v >= 65:
            out.append(hi)
        elif v <= 35:
            out.append(lo)
    return out


def rank_universe(
    scorecards: list[dict[str, Any]], *, profile: dict | None = None,
) -> list[Opportunity]:
    """Build, calibrate, and rank opportunities. Best screens first.

    Two calibration layers are attached to every name:
    - **cross-sectional** (``app.scanner.calibration``) — percentile vs *this*
      scan; drives the ranking when the universe is large enough, else falls back
      to the absolute composite.
    - **absolute / pinned** (``app.scanner.absolute_calibration``) — anchored to a
      fixed reference (the optional ``profile``) with named bands; universe-
      independent, for stable interpretation. Does not affect ordering.
    """
    opps = [build_opportunity(sc) for sc in scorecards]

    # local imports: avoid import cycle
    from app.scanner.absolute_calibration import calibrate_absolute
    from app.scanner.calibration import calibrate_universe
    calibrate_universe(opps)
    calibrate_absolute(opps, profile=profile)

    def sort_key(o: Opportunity) -> tuple[int, float, float]:
        cls = o.classification_calibrated or o.classification
        usable = 0 if cls == "insufficient_data" else 1
        score = o.composite_calibrated if o.calibration == "cross_sectional" else o.composite
        comp = score if score is not None else -1.0
        return (usable, comp, o.confidence)

    return sorted(opps, key=sort_key, reverse=True)
