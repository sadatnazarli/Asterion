#!/usr/bin/env python3
"""M13b — expand the scannable universe.

For each ticker: ensure its SEC data spine is ingested, pull price history, and
generate a real valuation scorecard into ``reports/``. The Opportunity Scanner
then ranks the larger set automatically (it reads ``reports/*_valuation_scorecard.json``).

Idempotent + resumable: a ticker whose scorecard already exists is skipped unless
``--force``. Failures are isolated and reported honestly — a ticker that can't be
ingested or scored is logged and skipped, never faked.

Usage:
    cd backend
    .venv/bin/python ../scripts/expand_universe.py --sector semiconductors
    .venv/bin/python ../scripts/expand_universe.py AMD AVGO QCOM
    .venv/bin/python ../scripts/expand_universe.py --starter          # curated mix
    .venv/bin/python ../scripts/expand_universe.py --file tickers.txt  # one symbol/line
    # flags: --force (regenerate existing), --limit N, --sleep SECONDS
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import psycopg  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.backtesting.dataset import load_price_history  # noqa: E402
from app.scoring.scorecard_generator import generate_real_scorecard  # noqa: E402

import bootstrap_ticker  # noqa: E402  (sibling script; path inserted above via scripts dir)

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
PCT_LOOKBACK_DAYS = 2200

# Curated sector lists (liquid, SEC-filing US names). Not exhaustive — a sane
# starting universe. Tickers already ingested are simply skipped.
SECTORS: dict[str, list[str]] = {
    "semiconductors": ["AMD", "AVGO", "QCOM", "AMAT", "LRCX", "ADI", "TXN", "INTC", "KLAC", "MRVL"],
    "megacap_tech": ["AAPL", "GOOGL", "AMZN", "NFLX", "ORCL", "CRM", "ADBE", "CSCO"],
    "payments_fintech": ["MA", "PYPL", "AXP", "FIS", "GPN"],
    "data_center": ["DELL", "SMCI", "ANET", "EQIX", "DLR"],
    "healthcare": ["UNH", "LLY", "JNJ", "ABBV", "MRK"],
}

# A small cross-sector default for a quick first expansion.
STARTER = ["AAPL", "GOOGL", "AMZN", "AMD", "AVGO", "QCOM", "ORCL", "CRM", "MA", "AXP", "UNH", "LLY"]


def scorecard_path(ticker: str) -> str:
    return os.path.join(REPORTS_DIR, f"{ticker.upper()}_valuation_scorecard.json")


def ingest_one(ticker: str) -> bool:
    """Ensure the SEC spine is ingested. Returns True on success."""
    try:
        # run(ticker, *, dry_run, use_cache, max_facts) -> int (0 ok)
        rc = bootstrap_ticker.run(ticker, dry_run=False, use_cache=True, max_facts=None)
        return rc == 0
    except Exception as exc:  # network / parse / DB
        print(f"  ✗ {ticker}: SEC ingest failed: {exc}")
        return False


def score_one(conn, ticker: str) -> dict | None:
    """Generate + persist a valuation scorecard. Returns the dict or None."""
    try:
        bars = load_price_history(ticker, lookback_days=PCT_LOOKBACK_DAYS)
        price_bars = [(b.d, b.close) for b in bars]
        closes = [b.close for b in bars][-300:]
        sc = generate_real_scorecard(
            conn, ticker, price_history=closes or None, price_bars=price_bars or None
        )
        with open(scorecard_path(ticker), "w", encoding="utf-8") as fh:
            json.dump(sc, fh, indent=2)
        return sc
    except Exception as exc:
        print(f"  ✗ {ticker}: scorecard generation failed: {exc}")
        return None


def resolve_tickers(args) -> list[str]:
    out: list[str] = []
    if args.starter:
        out += STARTER
    if args.sector:
        for s in args.sector:
            if s not in SECTORS:
                print(f"unknown sector '{s}'. Known: {', '.join(SECTORS)}")
                sys.exit(2)
            out += SECTORS[s]
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            out += [ln.strip().upper() for ln in fh if ln.strip() and not ln.startswith("#")]
    out += [t.upper() for t in args.tickers]
    # de-dup, preserve order
    seen: set[str] = set()
    uniq = [t for t in out if not (t in seen or seen.add(t))]
    if args.limit:
        uniq = uniq[: args.limit]
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser(description="Expand the scannable universe (SEC ingest + scorecard).")
    ap.add_argument("tickers", nargs="*", help="explicit symbols")
    ap.add_argument("--sector", action="append", help=f"preset(s): {', '.join(SECTORS)}")
    ap.add_argument("--starter", action="store_true", help="curated cross-sector starter set")
    ap.add_argument("--file", help="file with one symbol per line")
    ap.add_argument("--force", action="store_true", help="regenerate even if a scorecard exists")
    ap.add_argument("--limit", type=int, help="cap number of tickers")
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between tickers (SEC politeness)")
    args = ap.parse_args()

    tickers = resolve_tickers(args)
    if not tickers:
        ap.print_help()
        return 2

    print(f"Expanding universe: {len(tickers)} tickers — {', '.join(tickers)}")
    print("-" * 76)

    ingested, scored, skipped, failed = [], [], [], []

    with psycopg.connect(settings.db_dsn_sync) as conn:
        for i, t in enumerate(tickers, 1):
            exists = os.path.exists(scorecard_path(t))
            if exists and not args.force:
                print(f"[{i}/{len(tickers)}] {t}: scorecard exists — skip (use --force)")
                skipped.append(t)
                continue

            print(f"[{i}/{len(tickers)}] {t}: ingesting SEC spine …")
            if not ingest_one(t):
                failed.append(t)
                continue
            ingested.append(t)

            sc = score_one(conn, t)
            if sc is None:
                failed.append(t)
                continue
            conn.commit()
            cls = sc.get("classification")
            conf = sc.get("confidence")
            print(f"  ✓ {t}: scored — {cls} (conf {conf})")
            scored.append(t)

            if i < len(tickers):
                time.sleep(max(0.0, args.sleep))

    print("-" * 76)
    print(f"Done @ {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"  scored   ({len(scored)}): {', '.join(scored) or '—'}")
    print(f"  skipped  ({len(skipped)}): {', '.join(skipped) or '—'}")
    print(f"  failed   ({len(failed)}): {', '.join(failed) or '—'}")
    print(f"\nScanner will rank the new set automatically (/api/scanner/opportunities).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
