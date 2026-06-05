#!/usr/bin/env python3
"""Ingest daily prices for a given ticker or all tickers in the database.

Usage:
  python scripts/ingest_prices.py PLTR
  python scripts/ingest_prices.py --all
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# allow running as a plain script
BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db import repo
from app.db.session import transaction
from app.ingestion.prices import get_price_provider


def ingest_for_ticker(conn, ticker: str, start: date | None = None, end: date | None = None) -> int:
    provider = get_price_provider()
    
    # 1. resolve ticker_id from db
    cur = conn.execute("SELECT id FROM tickers WHERE symbol = %s", (ticker,))
    row = cur.fetchone()
    if not row:
        print(f"[asterion] Ticker {ticker} not found in DB. Run bootstrap_ticker.py first.", file=sys.stderr)
        return 0
    ticker_id = row[0]
    
    # 2. fetch prices
    try:
        prices = provider.fetch_daily(ticker, start=start, end=end)
    except Exception as e:
        print(f"[asterion] Failed to fetch prices for {ticker}: {e}", file=sys.stderr)
        return 0
        
    if not prices:
        print(f"[asterion] No prices found for {ticker}")
        return 0
        
    # 3. store in db
    stored = repo.bulk_insert_prices(conn, ticker_id, prices, provider.name)
    print(f"[asterion] Stored {stored} prices for {ticker} (using {provider.name})")
    return stored


def run(ticker: str | None, ingest_all: bool, start_str: str | None, end_str: str | None) -> int:
    start = date.fromisoformat(start_str) if start_str else None
    end = date.fromisoformat(end_str) if end_str else None

    with transaction() as conn:
        if ingest_all:
            cur = conn.execute("SELECT symbol FROM tickers ORDER BY symbol")
            symbols = [row[0] for row in cur.fetchall()]
            if not symbols:
                print("[asterion] No tickers found in DB.")
                return 0
                
            total_stored = 0
            for sym in symbols:
                total_stored += ingest_for_ticker(conn, sym, start, end)
            print(f"[asterion] Total prices stored: {total_stored}")
        elif ticker:
            ingest_for_ticker(conn, ticker.upper(), start, end)
        else:
            print("[asterion] Must specify a TICKER or --all", file=sys.stderr)
            return 1

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest daily prices using the configured provider")
    ap.add_argument("ticker", nargs="?", help="Ticker symbol to ingest")
    ap.add_argument("--all", action="store_true", help="Ingest prices for all tickers in DB")
    ap.add_argument("--start", help="Start date (YYYY-MM-DD)")
    ap.add_argument("--end", help="End date (YYYY-MM-DD)")
    
    args = ap.parse_args()
    return run(args.ticker, args.all, args.start, args.end)


if __name__ == "__main__":
    raise SystemExit(main())
