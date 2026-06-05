#!/usr/bin/env python3
"""Build the pinned reference distribution for absolute calibration.

Reads the current valuation scorecards, collects each component's raw score
distribution, and freezes it to reports/calibration_profile.json. The scanner
then anchors future scans to this *pinned* reference, so an absolute score means
the same thing across scans even as the live universe changes.

    cd backend && .venv/bin/python ../scripts/build_calibration_profile.py

Re-run to re-pin after a material universe expansion. This anchors to the
observed score distribution, not to forward outcomes — outcome fitting is future
work; the band rubric stays documented and deterministic meanwhile.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scanner.absolute_calibration import build_profile  # noqa: E402
from app.scanner.ranking import build_opportunity  # noqa: E402
from app.scanner.service import PROFILE_PATH, load_scorecards  # noqa: E402


def main() -> None:
    cards = load_scorecards()
    opps = [build_opportunity(c) for c in cards]
    dist = build_profile(opps)
    counts = {c: len(v) for c, v in dist.items()}
    payload = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "valuation_scorecards",
        "n_names": len(opps),
        "n_values": counts,
        "distribution": dist,
    }
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"Pinned calibration profile → {PROFILE_PATH}")
    print(f"  names: {len(opps)}  values/component: {counts}")
    print("  scanner will now anchor absolute scores to this frozen distribution.")


if __name__ == "__main__":
    main()
