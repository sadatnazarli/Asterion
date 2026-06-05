"""Cross-sectional score calibration for the scanner.

The raw 0-100 advanced scores are *absolute* formula outputs — a "70" is not
anchored to anything, so comparing names on raw scores overstates precision. This
module calibrates each component **relative to the ingested universe**: a name's
calibrated component is its percentile rank among peers that have that component.
A calibrated 70 then means "screens better than ~70% of the universe on this
factor" — which is exactly what a screen should rank on.

Properties:
- Deterministic, pure (no I/O, no LLM). Mid-rank percentile, ties handled.
- Honest about small universes: below ``MIN_UNIVERSE`` valued names there is no
  meaningful cross-section, so it falls back to *absolute* (calibrated == raw) and
  labels the method accordingly. This keeps tiny/synthetic sets unchanged.
- Never invents data: a missing component stays missing (no percentile assigned).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.scanner.ranking import WEIGHTS, _MIN_CONFIDENCE, _POOR, _WELL

if TYPE_CHECKING:  # avoid import cycle at runtime
    from app.scanner.ranking import Opportunity

# Need at least this many valued names for a cross-section to mean anything.
MIN_UNIVERSE = 8
_COMPONENTS = ("value", "quality", "safety", "change")


def percentile_rank(values: list[float], x: float) -> float:
    """Mid-rank percentile (0-100) of ``x`` within ``values``.

    percentile = 100 * (count(v < x) + 0.5*count(v == x)) / N. Stable for ties,
    deterministic, and 50 for a value equal to a single-element distribution.
    """
    n = len(values)
    if n == 0:
        return 50.0
    below = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return 100.0 * (below + 0.5 * equal) / n


def _classify(composite: float | None, confidence: float) -> str:
    if composite is None or confidence < _MIN_CONFIDENCE:
        return "insufficient_data"
    if composite >= _WELL:
        return "screens_well"
    if composite <= _POOR:
        return "screens_poorly"
    return "neutral"


def calibrate_universe(opps: list["Opportunity"], *, min_universe: int = MIN_UNIVERSE) -> dict:
    """Attach calibrated components/composite/percentiles to each Opportunity.

    Returns calibration metadata. Mutates each ``Opportunity`` in place, setting:
      - ``components_calibrated``  percentile-ranked components (0-100)
      - ``percentiles``            same values, named explicitly
      - ``composite_calibrated``   weight-renormalized calibrated composite
      - ``classification_calibrated``
      - ``calibration``            "cross_sectional" | "absolute"
    """
    # Build per-component distributions from every present raw component value.
    dists: dict[str, list[float]] = {c: [] for c in _COMPONENTS}
    for o in opps:
        for c in _COMPONENTS:
            v = o.components.get(c)
            if v is not None:
                dists[c].append(float(v))

    valued = sum(1 for o in opps if o.composite is not None)
    method = "cross_sectional" if valued >= min_universe else "absolute"

    for o in opps:
        if method == "absolute":
            # No meaningful cross-section: calibrated == raw, no percentiles.
            o.components_calibrated = dict(o.components)
            o.percentiles = None
            o.composite_calibrated = o.composite
            o.classification_calibrated = o.classification
            o.calibration = "absolute"
            continue

        cal: dict[str, float | None] = {}
        pct: dict[str, float | None] = {}
        for c in _COMPONENTS:
            v = o.components.get(c)
            if v is None:
                cal[c] = None
                pct[c] = None
            else:
                p = round(percentile_rank(dists[c], float(v)), 1)
                cal[c] = p
                pct[c] = p

        present = {k: v for k, v in cal.items() if v is not None}
        if present:
            wsum = sum(WEIGHTS[k] for k in present)
            comp = sum(cal[k] * WEIGHTS[k] for k in present) / wsum  # type: ignore[operator]
        else:
            comp = None

        o.components_calibrated = cal
        o.percentiles = pct
        o.composite_calibrated = None if comp is None else round(comp, 1)
        o.classification_calibrated = _classify(o.composite_calibrated, o.confidence)
        o.calibration = "cross_sectional"

    return {
        "method": method,
        "universe_valued": valued,
        "min_universe": min_universe,
        "components": list(_COMPONENTS),
        "note": (
            "Calibrated scores are cross-sectional percentiles within the ingested "
            "universe (higher = screens better than more peers on that factor)."
            if method == "cross_sectional" else
            f"Universe too small (<{min_universe} valued names) for cross-sectional "
            "calibration; showing absolute scores."
        ),
    }
