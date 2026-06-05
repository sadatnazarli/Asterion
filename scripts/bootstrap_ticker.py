#!/usr/bin/env python3
"""Bootstrap one ticker's data spine from SEC (and prices, best-effort).

    python scripts/bootstrap_ticker.py PLTR
    python scripts/bootstrap_ticker.py PLTR --dry-run         # no DB writes
    python scripts/bootstrap_ticker.py PLTR --no-cache        # force refetch
    python scripts/bootstrap_ticker.py PLTR --max-facts 2000  # cap facts (testing)

Pipeline: resolve CIK -> fetch submissions + companyfacts -> parse -> (prices,
soft) -> persist (unless --dry-run) -> print a clean summary. SEC is the source of
truth; a price failure never aborts the run. No LLM, no computed scores.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow running as a plain script: add backend/ to sys.path
BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ingestion.sec_edgar import (  # noqa: E402
    SECClient,
    parse_company_meta,
    parse_facts,
    parse_recent_filings,
)

FILING_FORMS = ("10-K", "10-Q", "8-K")


def _latest(filings: list[dict], form: str) -> dict | None:
    for f in filings:  # submissions.recent is newest-first
        if f["form_type"] == form:
            return f
    return None


def run(ticker: str, *, dry_run: bool, use_cache: bool, max_facts: int | None) -> int:
    ticker = ticker.upper()
    print(f"[asterion] bootstrapping {ticker}  (dry_run={dry_run})")

    with SECClient() as sec:
        cik = sec.resolve_cik(ticker, use_cache=use_cache)
        subs = sec.fetch_submissions(cik, use_cache=use_cache)
        meta = parse_company_meta(subs.data)
        recent = parse_recent_filings(subs.data, forms=FILING_FORMS)
        facts_res = sec.fetch_companyfacts(cik, use_cache=use_cache)
        facts = parse_facts(facts_res.data, limit=max_facts)

    latest_10k = _latest(recent, "10-K")
    latest_10q = _latest(recent, "10-Q")

    # prices: best-effort, never blocks SEC ingestion
    price_rows: list = []
    price_note = ""
    try:
        from app.ingestion.prices import get_price_provider

        price_rows = get_price_provider().fetch_daily(ticker)
        price_note = f"{len(price_rows)} daily bars"
    except Exception as e:  # soft fail by design
        price_note = f"skipped ({type(e).__name__}: {e})"

    stored_facts = stored_filings = stored_prices = 0
    if not dry_run:
        from app.db import repo
        from app.db.session import transaction

        primary_exch = meta["exchanges"][0] if meta["exchanges"] else None
        with transaction() as conn:
            company_id = repo.upsert_company(conn, meta)
            exch_id = repo.upsert_exchange(conn, primary_exch)
            repo.upsert_ticker(conn, company_id, ticker, exch_id)

            # provenance: submissions + companyfacts raw payloads
            subs_doc = repo.insert_raw_document(
                conn, company_id=company_id, document_type="sec_submissions",
                source_name=subs.provenance.source_name, source_url=subs.provenance.source_url,
                content_hash=subs.provenance.content_hash, storage_path=subs.provenance.storage_path,
            )
            repo.insert_raw_document(
                conn, company_id=company_id, document_type="sec_companyfacts",
                source_name=facts_res.provenance.source_name, source_url=facts_res.provenance.source_url,
                content_hash=facts_res.provenance.content_hash,
                storage_path=facts_res.provenance.storage_path,
            )
            for f in recent:
                repo.upsert_filing(conn, company_id, f, subs_doc)
            stored_filings = len(recent)

            stored_facts = repo.bulk_upsert_facts(
                conn, company_id, facts,
                source_url=facts_res.provenance.source_url,
                content_hash=facts_res.provenance.content_hash,
            )
            if price_rows:
                ticker_id = conn.execute(
                    "SELECT id FROM tickers WHERE symbol=%s AND company_id=%s",
                    (ticker, company_id),
                ).fetchone()[0]
                stored_prices = repo.bulk_insert_prices(conn, ticker_id, price_rows, "stooq")

    _summary(
        ticker, cik, meta, latest_10k, latest_10q, recent, facts,
        price_note, dry_run, stored_facts, stored_filings, stored_prices,
        subs.provenance.content_hash, facts_res.provenance.content_hash,
    )
    return 0


def _summary(ticker, cik, meta, k, q, recent, facts, price_note, dry_run,
             sf, sfil, sp, subs_hash, facts_hash) -> None:
    line = "─" * 60
    print(f"\n{line}\n  ASTERION — {ticker} data spine summary\n{line}")
    print(f"  Company        : {meta['name']}")
    print(f"  CIK            : {cik}")
    print(f"  SIC            : {meta.get('sic')} — {meta.get('sic_description')}")
    print(f"  Exchanges      : {', '.join(meta['exchanges']) or 'n/a'}")
    print(f"  Latest 10-K    : {k['filing_date'] if k else 'n/a'}  ({k['accession_number'] if k else ''})")
    print(f"  Latest 10-Q    : {q['filing_date'] if q else 'n/a'}  ({q['accession_number'] if q else ''})")
    print(f"  Recent filings : {len(recent)} (forms {','.join(FILING_FORMS)})")
    print(f"  XBRL facts     : {len(facts)} datapoints parsed")
    print(f"  Prices         : {price_note}")
    print(f"  Provenance     : submissions={subs_hash[:12]}…  facts={facts_hash[:12]}…")
    if dry_run:
        print(f"  Mode           : DRY-RUN (nothing written)")
    else:
        print(f"  Stored         : facts={sf}  filings={sfil}  prices={sp}")
    print(line)


def main() -> int:
    ap = argparse.ArgumentParser(description="Asterion ticker bootstrap (SEC data spine)")
    ap.add_argument("ticker")
    ap.add_argument("--dry-run", action="store_true", help="fetch + parse, no DB writes")
    ap.add_argument("--no-cache", action="store_true", help="force refetch from SEC")
    ap.add_argument("--max-facts", type=int, default=None, help="cap facts parsed (testing)")
    args = ap.parse_args()
    try:
        return run(
            args.ticker, dry_run=args.dry_run,
            use_cache=not args.no_cache, max_facts=args.max_facts,
        )
    except Exception as e:
        print(f"[asterion] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
