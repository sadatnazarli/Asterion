#!/usr/bin/env python3
"""M13 — analyze an IPO / private-company candidate (e.g. SpaceX -> SPCX).

Verifies the filing against SEC EDGAR, parses it, values it deterministically,
runs the IPO risk engine, and writes research-only reports. Never invents
numbers; never issues buy/sell.

Usage:
    cd backend
    .venv/bin/python ../scripts/analyze_ipo_candidate.py SPACEX
    .venv/bin/python ../scripts/analyze_ipo_candidate.py SPACEX --filing-url <SEC_URL>
    .venv/bin/python ../scripts/analyze_ipo_candidate.py SPACEX --unverified-news-mode

In --unverified-news-mode: summarizes only what is unverified, computes no final
valuation score, does not add to the portfolio, and is not shown as investable.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ipo import service  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze an IPO / private-company candidate.")
    ap.add_argument("ticker", help="candidate symbol (currently: SPACEX)")
    ap.add_argument("--filing-url", help="SEC filing URL to parse (else the latest is auto-found)")
    ap.add_argument("--unverified-news-mode", action="store_true",
                    help="treat as unverified news: no valuation, not investable")
    args = ap.parse_args()

    if args.ticker.upper() not in ("SPACEX", "SPCX"):
        print(f"Only SPACEX is wired in IPO mode for now (got {args.ticker}).")
        return 2

    print(f"IPO mode — analyzing {args.ticker.upper()} "
          f"({'unverified news' if args.unverified_news_mode else 'official filing'})")
    print("-" * 76)

    result = service.analyze_spacex(
        filing_url=args.filing_url,
        unverified_mode=args.unverified_news_mode,
        write=True,
    )

    v = result["verification"]
    sc = result["scorecard"]
    print(f"Official filing found : {v['filing_found']}")
    print(f"Registrant            : {v.get('registrant_name') or '—'} (CIK {v.get('cik') or '—'})")
    print(f"Proposed ticker       : {v.get('proposed_ticker') or '—'}")
    print(f"Filings               : {', '.join(sorted({f['form'] for f in v.get('filings', [])})) or '—'}")
    print(f"Classification        : {sc['classification']}  (confidence {sc['confidence']})")
    mc = sc['valuation']['metrics'].get('implied_market_cap_musd')
    evs = sc['valuation']['metrics'].get('ev_to_revenue') or sc['valuation']['metrics'].get('price_to_sales')
    print(f"Implied market cap    : {('$%.2fT' % (mc/1e6)) if mc else '—'}")
    print(f"EV/Revenue            : {('%.0fx' % evs) if evs else '—'}")
    print(f"Valuation method      : {sc['valuation']['method']}")
    print(f"Missing data          : {', '.join(sc['missing_data']) or '—'}")
    print("-" * 76)
    if "written" in result:
        for grp in result["written"].values():
            for kind, path in grp.items():
                print(f"  wrote {kind}: {path}")
    print("\nResearch only — not investment advice, no buy/sell recommendation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
