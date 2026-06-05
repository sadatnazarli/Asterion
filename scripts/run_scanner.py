#!/usr/bin/env python3
"""Run the Opportunity Scanner once and print the ranked screen.

Reads the latest valuation scorecards in reports/, ranks them deterministically,
writes reports/scanner_snapshot.json, and prints the table.

    cd backend && .venv/bin/python ../scripts/run_scanner.py

Not advice — research candidates with evidence + confidence only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scanner.service import refresh_snapshot  # noqa: E402


def main() -> None:
    snap = refresh_snapshot()
    print(f"\nOpportunity Scanner — {snap['universe']} names · scanned {snap['as_of']}")
    print(snap["disclaimer"])
    print("-" * 76)
    print(f"{'#':>2}  {'TICK':5} {'SCREEN':>6}  {'CLASS':18} {'CONF':>5}  drivers")
    for i, o in enumerate(snap["opportunities"], 1):
        comp = "—" if o["composite"] is None else f"{o['composite']:.0f}"
        drivers = ", ".join(o["drivers"][:2])
        print(f"{i:>2}  {o['ticker']:5} {comp:>6}  {o['classification']:18} "
              f"{o['confidence']:>5.2f}  {drivers}")
    print("-" * 76)
    print(f"Snapshot written to reports/scanner_snapshot.json")


if __name__ == "__main__":
    main()
