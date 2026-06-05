"""Database session helper — thin psycopg3 wrapper.

M1 uses raw SQL via psycopg (no ORM) for the ingestion path: it is explicit,
fast for bulk facts, and keeps the data spine transparent. A SQLAlchemy layer can
be added later for the API without disturbing ingestion.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.core.config import settings


def get_connection() -> psycopg.Connection:
    """Open a new psycopg connection from settings (caller manages lifecycle)."""
    return psycopg.connect(settings.db_dsn_sync)


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    """Connection + single transaction; commits on success, rolls back on error."""
    conn = get_connection()
    try:
        with conn.transaction():
            yield conn
    finally:
        conn.close()


def ping() -> bool:
    """True if the database is reachable."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
