"""M1 — migrations exist and are correctly ordered."""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"
EXPECTED = [
    "0001_extensions.sql",
    "0002_core_tables.sql",
    "0003_market_data_tables.sql",
    "0004_fundamentals_tables.sql",
    "0005_documents_and_filings_tables.sql",
    "0006_scores_and_audit_tables.sql",
    "0007_pgvector_embeddings.sql",
    "0008_m4_llm_audit.sql",
    "0009_portfolio_tables.sql",
    "0010_portfolio_partial_data.sql",
]


def test_all_expected_migrations_present() -> None:
    found = {p.name for p in MIGRATIONS.glob("[0-9]*.sql")}
    for name in EXPECTED:
        assert name in found, f"missing migration {name}"


def test_migrations_are_strictly_ordered() -> None:
    files = sorted(p.name for p in MIGRATIONS.glob("[0-9]*.sql"))
    nums = [int(re.match(r"(\d+)_", f).group(1)) for f in files]
    assert nums == sorted(nums)
    assert len(set(nums)) == len(nums), "duplicate migration numbers"
    assert files[: len(EXPECTED)] == EXPECTED


def test_extensions_are_guarded() -> None:
    # vector/timescaledb must be optional so M1 runs on plain Postgres.
    sql = (MIGRATIONS / "0001_extensions.sql").read_text()
    assert "pgcrypto" in sql
    assert "EXCEPTION" in sql  # guarded vector + timescaledb
