"""Absolute (pinned) score calibration for the scanner.

Cross-sectional calibration (``app.scanner.calibration``) ranks each name vs the
*current* scan — useful, but it floats: the same company can move just because
its peers changed. Absolute calibration is the complement. It anchors a raw
0-100 component score to a **fixed reference** so a given score means the same
thing across every scan, and attaches a documented, named band to it.

Two reference modes, in order of preference:

1. **Empirical profile** — a pinned per-component distribution saved to
   ``reports/calibration_profile.json`` (built by
   ``scripts/build_calibration_profile.py``). A raw score is converted to its
   percentile *against that frozen distribution* — anchored to observed history,
   not to whoever happens to be in today's scan.
2. **Rubric** (default, no profile present) — the raw score is used as-is and
   only the band rubric below is applied. Honest fallback: the bands are a
   documented interpretation, not yet fit to outcomes.

Either way the result is **universe-independent**: drop a name in or out of the
scan and everyone else's absolute band is unchanged.

Pure module — no LLM. The only optional I/O is reading the pinned profile, and
that is injected by the caller (``calibrate_absolute(opps, profile=...)``); the
core math is a pure function of its inputs. Missing components stay missing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.scanner.calibration import percentile_rank
from app.scanner.ranking import WEIGHTS

if TYPE_CHECKING:  # avoid import cycle at runtime
    from app.scanner.ranking import Opportunity

_COMPONENTS = ("value", "quality", "safety", "change")

# Fixed band edges on the 0-100 scale → five ordered bands. These do NOT move
# with the universe; that pinning is the whole point of "absolute".
#   [0,40) [40,55) [55,70) [70,85) [85,100]
BAND_EDGES: tuple[float, float, float, float] = (40.0, 55.0, 70.0, 85.0)

# Composite grade letters per band (coarse, audit-friendly headline).
COMPOSITE_GRADES: tuple[str, ...] = ("E", "D", "C", "B", "A")
COMPOSITE_LABELS: tuple[str, ...] = (
    "weak", "below_average", "solid", "strong", "exceptional",
)

# Concept-specific band labels — same numeric edges, readable per factor.
COMPONENT_LABELS: dict[str, tuple[str, ...]] = {
    "value":   ("rich", "full", "fair", "attractive", "deep_value"),
    "quality": ("weak", "thin", "adequate", "strong", "elite"),
    "safety":  ("fragile", "vulnerable", "stable", "resilient", "fortress"),
    "change":  ("stagnant", "soft", "steady", "improving", "inflecting"),
}


def band_index(score: float) -> int:
    """Return the band index 0..4 for ``score`` against the fixed edges."""
    for i, edge in enumerate(BAND_EDGES):
        if score < edge:
            return i
    return len(BAND_EDGES)  # == 4, the top band


def composite_band(score: float) -> str:
    return COMPOSITE_LABELS[band_index(score)]


def composite_grade(score: float) -> str:
    return COMPOSITE_GRADES[band_index(score)]


def component_band(component: str, score: float) -> str:
    labels = COMPONENT_LABELS.get(component, COMPOSITE_LABELS)
    return labels[band_index(score)]


def anchored_score(component: str, raw: float, profile: dict | None) -> float:
    """Map ``raw`` to its absolute, pinned 0-100 score.

    With an empirical ``profile`` (``{component: [sorted reference values]}``) the
    score is the percentile of ``raw`` within that *frozen* distribution. Without
    a profile it is the raw value unchanged (rubric mode).
    """
    if profile:
        ref = profile.get(component)
        if isinstance(ref, list) and ref:
            return round(percentile_rank([float(v) for v in ref], float(raw)), 1)
    return round(float(raw), 1)


def calibrate_absolute(
    opps: list["Opportunity"], *, profile: dict | None = None,
) -> dict:
    """Attach the absolute (pinned) calibration layer to each Opportunity.

    Sets, in place, on every ``Opportunity``:
      - ``components_anchored``  {component: anchored 0-100 | None}
      - ``components_band``      {component: band label | None}
      - ``composite_anchored``   weight-renormalized anchored composite | None
      - ``composite_band``       band label for the anchored composite | None
      - ``composite_grade``      A..E for the anchored composite | None
      - ``absolute_method``      "empirical_profile" | "rubric"

    Universe-independent: a name's bands depend only on its own scores and the
    pinned reference, never on the other names in this scan. Returns meta.
    """
    method = "empirical_profile" if profile else "rubric"

    for o in opps:
        anchored: dict[str, float | None] = {}
        bands: dict[str, str | None] = {}
        for c in _COMPONENTS:
            v = o.components.get(c)
            if v is None:
                anchored[c] = None
                bands[c] = None
            else:
                a = anchored_score(c, float(v), profile)
                anchored[c] = a
                bands[c] = component_band(c, a)

        present = {k: v for k, v in anchored.items() if v is not None}
        if present:
            wsum = sum(WEIGHTS[k] for k in present)
            comp = sum(anchored[k] * WEIGHTS[k] for k in present) / wsum  # type: ignore[operator]
            comp = round(comp, 1)
        else:
            comp = None

        o.components_anchored = anchored
        o.components_band = bands
        o.composite_anchored = comp
        o.composite_band = None if comp is None else composite_band(comp)
        o.composite_grade = None if comp is None else composite_grade(comp)
        o.absolute_method = method

    return {
        "method": method,
        "band_edges": list(BAND_EDGES),
        "composite_labels": list(COMPOSITE_LABELS),
        "composite_grades": list(COMPOSITE_GRADES),
        "component_labels": COMPONENT_LABELS,
        "note": (
            "Absolute scores are percentiles against a pinned empirical "
            "distribution (reports/calibration_profile.json); bands are fixed and "
            "do not move with the scan."
            if method == "empirical_profile" else
            "No pinned profile found — showing raw scores with a fixed band "
            "rubric. Bands are a documented interpretation, not yet fit to "
            "forward outcomes."
        ),
    }


# ── profile I/O (kept here so callers share one definition) ─────────────────
def build_profile(opps: list["Opportunity"]) -> dict[str, list[float]]:
    """Collect each component's present raw values into a reference distribution.

    This is what gets *pinned* to disk to anchor future scans. Built from the raw
    (uncalibrated) component scores so it captures the observed score spread.
    """
    profile: dict[str, list[float]] = {c: [] for c in _COMPONENTS}
    for o in opps:
        for c in _COMPONENTS:
            v = o.components.get(c)
            if v is not None:
                profile[c].append(round(float(v), 4))
    for c in _COMPONENTS:
        profile[c].sort()
    return profile
