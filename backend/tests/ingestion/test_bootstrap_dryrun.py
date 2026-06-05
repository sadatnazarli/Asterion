"""M1 — bootstrap runs in dry-run mode without touching the database.

We monkeypatch the SEC client with a fake (no network) and point the DB at an
unroutable host. If dry-run still returns 0, it proves the dry-run path performs
no DB access.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP = REPO / "scripts" / "bootstrap_ticker.py"


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location("bootstrap_ticker", BOOTSTRAP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_SUBS = {
    "cik": "1321655", "name": "Test Co", "sic": "7372",
    "sicDescription": "Software", "exchanges": ["Nasdaq"], "tickers": ["PLTR"],
    "addresses": {"business": {"stateOrCountry": "CO"}},
    "filings": {"recent": {
        "accessionNumber": ["a-1", "a-2"], "form": ["10-K", "10-Q"],
        "filingDate": ["2025-02-01", "2025-05-01"],
        "reportDate": ["2024-12-31", "2025-03-31"],
        "primaryDocument": ["k.htm", "q.htm"],
    }},
}
_FACTS = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
    {"val": 100, "end": "2024-12-31", "fy": 2024, "fp": "FY", "form": "10-K", "accn": "a-1"}
]}}}}}


def _prov(h: str):
    return SimpleNamespace(
        source_name="SEC EDGAR", source_url="http://x", content_hash=h, storage_path=None
    )


class _FakeSEC:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def resolve_cik(self, ticker, use_cache=True):
        return "0001321655"

    def fetch_submissions(self, cik, use_cache=True):
        return SimpleNamespace(data=_SUBS, provenance=_prov("subs" + "0" * 60))

    def fetch_companyfacts(self, cik, use_cache=True):
        return SimpleNamespace(data=_FACTS, provenance=_prov("facts" + "0" * 60))


def test_bootstrap_dry_run_no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    # DB intentionally unroutable: dry-run must not connect.
    monkeypatch.setenv("ASTERION_DB_HOST", "256.256.256.256")
    mod = _load_bootstrap()
    monkeypatch.setattr(mod, "SECClient", _FakeSEC)
    rc = mod.run("PLTR", dry_run=True, use_cache=True, max_facts=None)
    assert rc == 0


def test_bootstrap_summary_parses_latest_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_bootstrap()
    recent = [
        {"form_type": "10-K", "accession_number": "a-1", "filing_date": "2025-02-01"},
        {"form_type": "10-Q", "accession_number": "a-2", "filing_date": "2025-05-01"},
    ]
    assert mod._latest(recent, "10-K")["accession_number"] == "a-1"
    assert mod._latest(recent, "10-Q")["accession_number"] == "a-2"
    assert mod._latest(recent, "S-1") is None
