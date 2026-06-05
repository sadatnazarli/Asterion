"""Generate a single ticker's valuation scorecard from REAL data (M10).

Pre-M10 this script hardcoded mock ratios and CLI-default growth/impact. It now
delegates to app.scoring.scorecard_generator (SEC facts + reverse-DCF + price
history) — no mock constants. For the full 9-ticker regen + variance report use
scripts/regenerate_scorecards.py.

Usage:
    .venv/bin/python ../scripts/generate_valuation_scorecard.py NVDA
    .venv/bin/python ../scripts/generate_valuation_scorecard.py NVDA --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import psycopg  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.backtesting.dataset import load_price_history  # noqa: E402
from app.scoring.scorecard_generator import generate_real_scorecard  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a real valuation scorecard")
    ap.add_argument("ticker", type=str)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    symbol = args.ticker.upper()
    closes = [b.close for b in load_price_history(symbol, lookback_days=400)]
    with psycopg.connect(settings.db_dsn_sync) as conn:
        sc = generate_real_scorecard(conn, symbol, price_history=closes or None)

    if sc.get("error"):
        print(f"ERROR: {sc['error']} for {symbol}")
        return 1

    if args.dry_run:
        print(json.dumps(sc, indent=2))
        return 0

    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    json_path = os.path.join(report_dir, f"{symbol}_valuation_scorecard.json")
    with open(json_path, "w") as f:
        json.dump(sc, f, indent=2)
    print(f"Real valuation scorecard written: {json_path}")
    print(f"  classification={sc.get('classification')} "
          f"missing={sc.get('input_missing_flags')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
