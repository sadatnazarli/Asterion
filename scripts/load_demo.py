#!/usr/bin/env python3
"""Public demo mode — seed reports/ from the tracked sample dataset.

Copies the sanitized demo scorecards (public-company valuation data, the SpaceX
IPO scorecard, and SEC verification) from examples/demo/reports/ into reports/,
then pins the absolute-calibration profile and builds the scanner snapshot. No
Postgres, no SEC calls, no API keys — just deterministic file-backed data so a
fresh clone can explore the Scanner, IPO mode, and Reports immediately.

    cd backend && .venv/bin/python ../scripts/load_demo.py

Idempotent: re-running overwrites the demo reports and rebuilds the snapshot.
Demo data only — no personal holdings, broker data, or secrets.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.scanner.absolute_calibration import build_profile  # noqa: E402
from app.scanner.ranking import build_opportunity  # noqa: E402
from app.scanner.service import (  # noqa: E402
    PROFILE_PATH,
    REPORTS_DIR,
    load_scorecards,
    refresh_snapshot,
)

DEMO_DIR = ROOT / "examples" / "demo" / "reports"


def main() -> None:
    if not DEMO_DIR.is_dir():
        sys.exit(f"demo dataset missing: {DEMO_DIR}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in sorted(DEMO_DIR.glob("*")):
        if src.is_file():
            shutil.copy2(src, REPORTS_DIR / src.name)
            copied += 1
    print(f"• Seeded {copied} demo report files → {REPORTS_DIR}")

    # Pin the absolute-calibration reference distribution from the demo universe.
    opps = [build_opportunity(c) for c in load_scorecards()]
    dist = build_profile(opps)
    payload = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "demo_dataset",
        "n_names": len(opps),
        "n_values": {c: len(v) for c, v in dist.items()},
        "distribution": dist,
    }
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"• Pinned calibration profile ({len(opps)} names) → {PROFILE_PATH}")

    snap = refresh_snapshot()
    print(f"• Built scanner snapshot: {snap['universe']} names")
    print("\nDemo ready. Start the app (make start), then open:")
    print("  http://localhost:3000/scanner      ranked screen (calibrated)")
    print("  http://localhost:3000/ipo/SPACEX   IPO / private-company mode")
    print("  http://localhost:3000/reports      generated scorecards")


if __name__ == "__main__":
    main()
