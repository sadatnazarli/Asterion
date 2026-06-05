#!/usr/bin/env python3
"""Compute deterministic financial ratios for a ticker.

    python scripts/compute_ratios.py PLTR
    python scripts/compute_ratios.py PLTR --dry-run      # compute but don't store
    python scripts/compute_ratios.py PLTR --periods 5    # last N annual periods

Pipeline: resolve company_id → discover FY periods → fetch XBRL facts →
compute all ratios → store in financial_ratios → print summary.
No LLM, no market data, no investment advice. Pure SEC data + arithmetic.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# allow running as a plain script: add backend/ to sys.path
BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.session import get_connection, transaction  # noqa: E402
from app.quant.scoring_inputs import (  # noqa: E402
    compute_all_ratios,
    fetch_period_data,
    generate_missing_data_report,
    get_annual_periods,
    store_ratios,
)


def _resolve_company(conn, ticker: str) -> tuple[int, str]:
    """Resolve ticker → (company_id, company_name)."""
    row = conn.execute(
        """
        SELECT c.id, c.name
        FROM companies c
        JOIN tickers t ON t.company_id = c.id
        WHERE t.symbol = %s
        LIMIT 1
        """,
        (ticker.upper(),),
    ).fetchone()
    if not row:
        raise SystemExit(f"[asterion] ERROR: ticker {ticker!r} not found in database. Run bootstrap_ticker.py first.")
    return row[0], row[1]


def run(ticker: str, *, dry_run: bool, max_periods: int) -> int:
    ticker = ticker.upper()
    print(f"[asterion] computing ratios for {ticker}  (dry_run={dry_run})")

    conn = get_connection()
    try:
        company_id, company_name = _resolve_company(conn, ticker)
        print(f"  Company     : {company_name} (id={company_id})")

        periods = get_annual_periods(conn, company_id, limit=max_periods)
        if not periods:
            print(f"[asterion] ERROR: no annual periods found for {ticker}. Ensure SEC data is ingested.")
            return 1

        print(f"  Periods     : {len(periods)} annual (FY)")

        all_results = []
        total_stored = 0

        for i, period in enumerate(periods):
            pe = period["period_end"]
            fy = period.get("fiscal_year")
            prior_pe = periods[i + 1]["period_end"] if i + 1 < len(periods) else None

            results = compute_all_ratios(
                conn, company_id, pe,
                prior_period_end=prior_pe,
                fiscal_year=fy,
                fiscal_period="FY",
            )
            all_results.extend(results)

            if not dry_run:
                with conn.transaction():
                    stored = store_ratios(conn, company_id, pe, results)
                    total_stored += stored

            computed = sum(1 for r in results if r.value is not None)
            missing = sum(1 for r in results if r.value is None)
            print(f"  FY{fy or '?'} ({pe}): {computed} computed, {missing} missing"
                  f"{f', {stored} stored' if not dry_run else ''}")

        # --- Summary ---
        missing_report = generate_missing_data_report(all_results)
        formula_names = sorted({r.name for r in all_results})
        computed_names = sorted({r.name for r in all_results if r.value is not None})
        missing_names = sorted({r.name for r in all_results if all(
            rr.value is None for rr in all_results if rr.name == r.name
        )})

        line = "─" * 64
        print(f"\n{line}")
        print(f"  ASTERION M2 — {ticker} ratio computation summary")
        print(f"{line}")
        print(f"  Company           : {company_name}")
        print(f"  Periods processed : {len(periods)}")
        print(f"  Total formulas    : {len(formula_names)}")
        print(f"  Formulas with data: {len(computed_names)}")
        if not dry_run:
            print(f"  Rows stored       : {total_stored}")
        else:
            print(f"  Mode              : DRY-RUN (nothing stored)")

        print(f"\n  ── Ratios computed ──")
        for name in computed_names:
            vals = [r for r in all_results if r.name == name and r.value is not None]
            latest = vals[0] if vals else None
            print(f"    {name:30s}  latest={latest.value:>12.4f}  periods={len(vals)}" if latest else f"    {name}")

        if missing_names:
            print(f"\n  ── Always missing (across all periods) ──")
            for name in missing_names:
                flags = missing_report.get(name, [])
                print(f"    {name:30s}  reason: {', '.join(flags) if flags else 'no data'}")

        if missing_report:
            print(f"\n  ── Missing data report ──")
            for fname, flags in sorted(missing_report.items()):
                if fname not in missing_names:
                    print(f"    {fname:30s}  partial: {', '.join(flags)}")

        print(f"\n  ── Formulas implemented ──")
        for i, name in enumerate(formula_names, 1):
            print(f"    {i:2d}. {name}")

        print(f"\n  ── Next step ──")
        print(f"    M3: RAG pipeline — embed SEC filings, build retrieval for qualitative analysis")
        print(line)

        return 0

    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Asterion M2 — compute deterministic financial ratios from SEC data"
    )
    ap.add_argument("ticker", help="Stock ticker symbol (e.g., PLTR)")
    ap.add_argument("--dry-run", action="store_true", help="compute but don't store to DB")
    ap.add_argument("--periods", type=int, default=10, help="max annual periods to process (default: 10)")
    args = ap.parse_args()
    try:
        return run(args.ticker, dry_run=args.dry_run, max_periods=args.periods)
    except Exception as e:
        print(f"[asterion] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
