#!/usr/bin/env python3
"""Minimal, dependency-light migration runner for Asterion.

Applies ordered SQL files in backend/app/db/migrations/ (NNNN_*.sql) inside a
transaction each, tracking applied files in a schema_migrations table. Idempotent:
already-applied files are skipped. Templating: occurrences of ${EMBED_DIM} are
replaced with ASTERION_EMBED_DIM so the pgvector column matches the embed model.

Usage:
    python scripts/migrate.py            # apply pending
    python scripts/migrate.py --status   # list applied/pending

DDL files themselves land in M1; this runner is part of the foundation so the
contract (numbered raw SQL + tracking table) is fixed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "backend" / "app" / "db" / "migrations"


def _dsn() -> str:
    host = os.getenv("ASTERION_DB_HOST", "localhost")
    port = os.getenv("ASTERION_DB_PORT", "5432")
    name = os.getenv("ASTERION_DB_NAME", "asterion")
    user = os.getenv("ASTERION_DB_USER", "asterion")
    pw = os.getenv("ASTERION_DB_PASSWORD", "change_me")
    return f"postgresql://{user}:{pw}@{host}:{port}/{name}"


def _render(sql: str) -> str:
    return sql.replace("${EMBED_DIM}", os.getenv("ASTERION_EMBED_DIM", "768"))


def main() -> int:
    files = sorted(MIGRATIONS_DIR.glob("[0-9]*.sql"))
    status_only = "--status" in sys.argv

    if not files:
        print(f"No migrations in {MIGRATIONS_DIR} yet (added in milestone M1).")
        return 0

    try:
        import psycopg  # type: ignore
    except ImportError:
        print("psycopg not installed. `pip install -e backend[dev]` first.", file=sys.stderr)
        return 1

    with psycopg.connect(_dsn(), autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename text PRIMARY KEY, applied_at timestamptz DEFAULT now())"
        )
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}

        for f in files:
            pending = f.name not in applied
            if status_only:
                print(f"[{'applied' if not pending else 'PENDING'}] {f.name}")
                continue
            if not pending:
                continue
            print(f"applying {f.name} ...")
            with conn.transaction():
                conn.execute(_render(f.read_text()))
                conn.execute(
                    "INSERT INTO schema_migrations(filename) VALUES (%s)", (f.name,)
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
