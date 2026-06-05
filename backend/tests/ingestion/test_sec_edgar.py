"""M1 — SEC ingestion units: UA validation, CIK norm, hashing, parsing.

All hermetic (no network)."""
from __future__ import annotations

import pytest

from app.core.provenance import cik_url_fragment, content_hash, normalize_cik
from app.ingestion.sec_edgar import (
    SECError,
    parse_company_meta,
    parse_facts,
    parse_recent_filings,
    validate_user_agent,
)


# --- User-Agent validation -------------------------------------------------
def test_user_agent_accepts_real_value() -> None:
    ua = "Asterion Research (real.person@gmail.com)"
    assert validate_user_agent(ua) == ua


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "   ",
        "Asterion Research",  # no email
        "Asterion (set-your-email@example.com)",  # placeholder marker
        "test (you@example.com)",  # example.com placeholder
    ],
)
def test_user_agent_rejects_bad_values(bad: str | None) -> None:
    with pytest.raises(SECError):
        validate_user_agent(bad)


# --- CIK normalization -----------------------------------------------------
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1321655", "0001321655"),
        (1321655, "0001321655"),
        ("CIK0001321655", "0001321655"),
        ("0001321655", "0001321655"),
    ],
)
def test_normalize_cik(raw: object, expected: str) -> None:
    assert normalize_cik(raw) == expected


@pytest.mark.parametrize("bad", ["", "abc", "CIK", "123abc", "123456789012"])
def test_normalize_cik_rejects_bad(bad: str) -> None:
    with pytest.raises(ValueError):
        normalize_cik(bad)


def test_cik_url_fragment() -> None:
    assert cik_url_fragment("1321655") == "CIK0001321655"


# --- content hash ----------------------------------------------------------
def test_content_hash_is_deterministic_and_sensitive() -> None:
    assert content_hash("abc") == content_hash(b"abc")
    assert content_hash("abc") != content_hash("abd")
    assert len(content_hash("x")) == 64  # sha256 hex


# --- parsing ---------------------------------------------------------------
SUBMISSIONS_FIXTURE = {
    "cik": "1321655",
    "name": "Test Co",
    "sic": "7372",
    "sicDescription": "Services-Prepackaged Software",
    "fiscalYearEnd": "1231",
    "tickers": ["PLTR"],
    "exchanges": ["Nasdaq"],
    "addresses": {"business": {"stateOrCountry": "CO"}},
    "filings": {
        "recent": {
            "accessionNumber": ["a-1", "a-2", "a-3"],
            "form": ["10-K", "8-K", "10-Q"],
            "filingDate": ["2025-02-01", "2025-03-01", "2025-05-01"],
            "reportDate": ["2024-12-31", "", "2025-03-31"],
            "primaryDocument": ["k.htm", "8k.htm", "q.htm"],
        }
    },
}

FACTS_FIXTURE = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"val": 100, "end": "2024-12-31", "fy": 2024, "fp": "FY",
                         "form": "10-K", "accn": "a-1", "filed": "2025-02-01"},
                        {"val": None, "end": "2023-12-31"},  # dropped (null val)
                    ]
                }
            }
        }
    }
}


def test_parse_company_meta() -> None:
    meta = parse_company_meta(SUBMISSIONS_FIXTURE)
    assert meta["cik"] == "0001321655"
    assert meta["name"] == "Test Co"
    assert meta["tickers"] == ["PLTR"]
    assert meta["exchanges"] == ["Nasdaq"]


def test_parse_recent_filings_filters_and_orders() -> None:
    only_k = parse_recent_filings(SUBMISSIONS_FIXTURE, forms=("10-K",))
    assert len(only_k) == 1 and only_k[0]["accession_number"] == "a-1"
    kq = parse_recent_filings(SUBMISSIONS_FIXTURE, forms=("10-K", "10-Q", "8-K"))
    assert len(kq) == 3


def test_parse_facts_drops_nulls() -> None:
    flat = parse_facts(FACTS_FIXTURE)
    assert len(flat) == 1
    f = flat[0]
    assert f["concept"] == "Revenues" and f["value"] == 100 and f["unit"] == "USD"
    assert f["accession_number"] == "a-1"
