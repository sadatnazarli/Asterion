#!/usr/bin/env python3
"""Generate a Verifex + Asterion decision-intelligence report.

Merges Asterion financial risk with Verifex compliance/entity risk into one
evidence-backed view. Research only — no buy/sell, no advice.

Public ticker:
    cd backend && .venv/bin/python ../scripts/generate_decision_report.py META

Private company (legal name):
    .venv/bin/python ../scripts/generate_decision_report.py \
        "Space Exploration Technologies Corp" --private

Writes reports/decision_intelligence_{KEY}.{md,json}. Verifex is optional: with
no key/URL configured the compliance half is reported as provider_unavailable
(not "clean") and the report is still produced.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.decision_intelligence.service import generate_decision_report  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Verifex + Asterion decision report")
    ap.add_argument("identifier", help="public ticker (META) or legal name (with --private)")
    ap.add_argument("--private", action="store_true", help="treat identifier as a private legal name")
    ap.add_argument("--entity-name", default=None, help="override the display/legal name")
    ap.add_argument("--no-write", action="store_true", help="do not write report files")
    args = ap.parse_args()

    decision = generate_decision_report(
        args.identifier,
        private=args.private,
        entity_name=args.entity_name,
        write=not args.no_write,
    )

    print(f"\nDecision Intelligence — {decision.entity_name}")
    print(f"  classification : {decision.classification}")
    print(f"  combined risk  : {decision.combined_risk_level}")
    print(f"  confidence     : {decision.confidence:.2f}")
    print(f"  financial      : {decision.financial_summary.headline}")
    print(f"  compliance     : {decision.compliance_summary.headline}")
    if decision.missing_data:
        print(f"  missing        : {', '.join(decision.missing_data)}")
    print("  next steps:")
    for s in decision.recommended_next_research_steps:
        print(f"    - {s}")
    if not args.no_write:
        key = decision.ticker or decision.entity_name
        print(f"\n  wrote reports/decision_intelligence_*.{{md,json}} for {key}")


if __name__ == "__main__":
    main()
