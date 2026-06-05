"""Repository — idempotent upserts for the M1 data spine.

All functions take an open psycopg connection (inside a transaction) so the
caller controls atomicity. Every write is idempotent (ON CONFLICT) so re-running
the bootstrap never duplicates rows. No numbers are computed here; only vendor /
SEC data is persisted with provenance.
"""
from __future__ import annotations

from typing import Any, Sequence

import psycopg
from psycopg.types.json import Jsonb


def upsert_exchange(conn: psycopg.Connection, code: str | None) -> int | None:
    if not code:
        return None
    row = conn.execute(
        """
        INSERT INTO exchanges (code) VALUES (%s)
        ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code
        RETURNING id
        """,
        (code,),
    ).fetchone()
    return row[0] if row else None


def upsert_company(conn: psycopg.Connection, meta: dict[str, Any]) -> int:
    """Insert/update a company by CIK; returns company_id. Preserves is_active."""
    row = conn.execute(
        """
        INSERT INTO companies (cik, name, sic, sic_description, fiscal_year_end, country)
        VALUES (%(cik)s, %(name)s, %(sic)s, %(sic_description)s, %(fiscal_year_end)s, %(country)s)
        ON CONFLICT (cik) DO UPDATE SET
            name = EXCLUDED.name,
            sic = EXCLUDED.sic,
            sic_description = EXCLUDED.sic_description,
            fiscal_year_end = EXCLUDED.fiscal_year_end,
            country = EXCLUDED.country,
            updated_at = now()
        RETURNING id
        """,
        meta,
    ).fetchone()
    assert row is not None
    return row[0]


def upsert_ticker(
    conn: psycopg.Connection,
    company_id: int,
    symbol: str,
    exchange_id: int | None = None,
    is_primary: bool = True,
) -> int:
    row = conn.execute(
        """
        INSERT INTO tickers (company_id, symbol, exchange_id, is_primary)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (symbol, company_id) DO UPDATE SET
            exchange_id = COALESCE(EXCLUDED.exchange_id, tickers.exchange_id),
            is_primary = EXCLUDED.is_primary
        RETURNING id
        """,
        (company_id, symbol, exchange_id, is_primary),
    ).fetchone()
    assert row is not None
    return row[0]


def insert_raw_document(
    conn: psycopg.Connection,
    *,
    company_id: int | None,
    document_type: str,
    source_name: str,
    source_url: str,
    content_hash: str,
    storage_path: str | None,
    accession_number: str | None = None,
    license_note: str | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    """Insert a raw document; dedup on content_hash. Returns existing id if seen."""
    row = conn.execute(
        """
        INSERT INTO raw_documents
            (company_id, document_type, source_name, source_url, accession_number,
             license_note, storage_path, content_hash, meta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO UPDATE SET retrieved_at = raw_documents.retrieved_at
        RETURNING id
        """,
        (
            company_id, document_type, source_name, source_url, accession_number,
            license_note, storage_path, content_hash, Jsonb(meta or {}),
        ),
    ).fetchone()
    assert row is not None
    return row[0]


def upsert_filing(
    conn: psycopg.Connection, company_id: int, f: dict[str, Any], raw_document_id: int | None
) -> int:
    row = conn.execute(
        """
        INSERT INTO filings
            (company_id, accession_number, form_type, filing_date, period_of_report,
             primary_doc, raw_document_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (accession_number) DO UPDATE SET
            form_type = EXCLUDED.form_type,
            filing_date = EXCLUDED.filing_date,
            period_of_report = EXCLUDED.period_of_report,
            primary_doc = EXCLUDED.primary_doc
        RETURNING id
        """,
        (
            company_id,
            f["accession_number"],
            f.get("form_type"),
            _nz(f.get("filing_date")),
            _nz(f.get("period_of_report")),
            f.get("primary_doc"),
            raw_document_id,
        ),
    ).fetchone()
    assert row is not None
    return row[0]


def bulk_upsert_facts(
    conn: psycopg.Connection,
    company_id: int,
    facts: Sequence[dict[str, Any]],
    *,
    source_url: str,
    content_hash: str,
    batch: int = 1000,
) -> int:
    """Bulk insert XBRL facts. Idempotent on the natural unique key. Returns count attempted."""
    sql = """
        INSERT INTO financial_facts
            (company_id, taxonomy, concept, unit, value, period_start, period_end,
             fiscal_year, fiscal_period, form, filed, frame, accession_number,
             source_url, content_hash)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (company_id, taxonomy, concept, unit, period_end, fiscal_period, accession_number)
        DO UPDATE SET value = EXCLUDED.value, retrieved_at = now()
    """
    rows = [
        (
            company_id, f["taxonomy"], f["concept"], f["unit"], f["value"],
            _nz(f.get("period_start")), _nz(f["period_end"]), f.get("fiscal_year"),
            f.get("fiscal_period"), f.get("form"), _nz(f.get("filed")), f.get("frame"),
            f.get("accession_number"), source_url, content_hash,
        )
        for f in facts
        if f.get("period_end") and f.get("value") is not None
    ]
    with conn.cursor() as cur:
        for i in range(0, len(rows), batch):
            cur.executemany(sql, rows[i : i + batch])
    return len(rows)


def bulk_insert_prices(
    conn: psycopg.Connection, ticker_id: int, rows: Sequence[Any], source: str
) -> int:
    sql = """
        INSERT INTO prices_daily
            (ticker_id, date, open, high, low, close, adj_close, volume, source)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (ticker_id, date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
            close=EXCLUDED.close, adj_close=EXCLUDED.adj_close, volume=EXCLUDED.volume,
            source=EXCLUDED.source, retrieved_at=now()
    """
    data = [
        (ticker_id, r.date, r.open, r.high, r.low, r.close, r.adj_close, r.volume, source)
        for r in rows
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, data)
    return len(data)


def counts_for_company(conn: psycopg.Connection, company_id: int) -> dict[str, int]:
    q = lambda sql: conn.execute(sql, (company_id,)).fetchone()[0]  # noqa: E731
    return {
        "facts": q("SELECT count(*) FROM financial_facts WHERE company_id=%s"),
        "filings": q("SELECT count(*) FROM filings WHERE company_id=%s"),
    }


def _nz(v: Any) -> Any:
    """Normalize empty string to NULL for DATE columns."""
    return None if v in ("", None) else v
