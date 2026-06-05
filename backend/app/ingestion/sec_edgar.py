"""SEC EDGAR ingestion — submissions + companyfacts.

Fair-access compliant:
  * a descriptive User-Agent (name + email) is REQUIRED by SEC; we validate it and
    refuse to call with the placeholder value;
  * requests are rate-limited to < 10/sec (configurable, default 8);
  * transient failures (429 / 5xx / network) retry with exponential backoff;
  * every fetched payload is cached to data/cache/sec and returned with provenance
    (source_url, retrieved_at, content_hash).

No database access here — this module only fetches + parses + stamps provenance.
Persistence is the caller's job (see scripts/bootstrap_ticker.py). No LLM is used.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.provenance import content_hash, normalize_cik

# SEC endpoints
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

_PLACEHOLDER_UA_MARKERS = ("set-your-email", "example.com", "you@", "your-email")


class SECError(RuntimeError):
    pass


class RetriableHTTP(SECError):
    """Raised for 429/5xx so tenacity retries; non-retriable errors raise SECError."""


def validate_user_agent(ua: str | None) -> str:
    """Ensure the SEC User-Agent is real (contains an email) and not a placeholder.

    SEC bans anonymous / abusive clients. Fail loudly *before* making a request.
    """
    if not ua or not ua.strip():
        raise SECError(
            "ASTERION_SEC_USER_AGENT is empty. SEC requires a descriptive "
            "User-Agent containing your email, e.g. 'Asterion Research (you@mail.com)'."
        )
    if "@" not in ua:
        raise SECError(f"ASTERION_SEC_USER_AGENT must contain an email: {ua!r}")
    low = ua.lower()
    if any(m in low for m in _PLACEHOLDER_UA_MARKERS):
        raise SECError(
            f"ASTERION_SEC_USER_AGENT still looks like a placeholder: {ua!r}. "
            "Set your real email in .env."
        )
    return ua.strip()


@dataclass
class Provenance:
    source_name: str
    source_url: str
    retrieved_at: str
    content_hash: str
    storage_path: str | None = None


@dataclass
class FetchResult:
    data: Any
    provenance: Provenance
    raw_bytes: bytes = field(repr=False, default=b"")


class _RateLimiter:
    """Single-process min-interval gate keeping us under max_rps."""

    def __init__(self, max_rps: float) -> None:
        self._min_interval = 1.0 / max(0.1, max_rps)
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last
        if delta < self._min_interval:
            time.sleep(self._min_interval - delta)
        self._last = time.monotonic()


class SECClient:
    """Rate-limited SEC EDGAR client with backoff, caching, and provenance."""

    def __init__(
        self,
        user_agent: str | None = None,
        max_rps: int | None = None,
        cache_dir: str | Path | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.user_agent = validate_user_agent(user_agent or settings.sec_user_agent)
        self.max_rps = max_rps or settings.sec_max_rps
        self._limiter = _RateLimiter(self.max_rps)
        self._cache_dir = Path(cache_dir or Path(settings.data_dir) / "cache" / "sec")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(
            timeout=timeout_s,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=True,
        )

    # -- low level ----------------------------------------------------------
    @retry(
        retry=retry_if_exception_type(RetriableHTTP),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _get(self, url: str) -> bytes:
        self._limiter.wait()
        try:
            resp = self._client.get(url)
        except httpx.TransportError as e:  # network blip -> retry
            raise RetriableHTTP(f"transport error for {url}: {e}") from e
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            raise RetriableHTTP(f"HTTP {resp.status_code} for {url}")
        if resp.status_code == 404:
            raise SECError(f"404 not found: {url}")
        if resp.status_code != 200:
            raise SECError(f"HTTP {resp.status_code} for {url}")
        return resp.content

    def _fetch_raw(
        self, url: str, cache_key: str, extension: str, use_cache: bool
    ) -> FetchResult:
        cache_path = self._cache_dir / f"{cache_key}.{extension}"
        if use_cache and cache_path.exists():
            raw = cache_path.read_bytes()
            retrieved_at = datetime.fromtimestamp(
                cache_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        else:
            raw = self._get(url)
            cache_path.write_bytes(raw)
            retrieved_at = datetime.now(timezone.utc).isoformat()
        prov = Provenance(
            source_name="SEC EDGAR",
            source_url=url,
            retrieved_at=retrieved_at,
            content_hash=content_hash(raw),
            storage_path=str(cache_path),
        )
        return FetchResult(data=None, provenance=prov, raw_bytes=raw)

    def _fetch_json(
        self, url: str, document_type: str, cache_key: str, use_cache: bool
    ) -> FetchResult:
        cache_path = self._cache_dir / f"{cache_key}.json"
        if use_cache and cache_path.exists():
            raw = cache_path.read_bytes()
            retrieved_at = datetime.fromtimestamp(
                cache_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        else:
            raw = self._get(url)
            cache_path.write_bytes(raw)
            retrieved_at = datetime.now(timezone.utc).isoformat()
        prov = Provenance(
            source_name="SEC EDGAR",
            source_url=url,
            retrieved_at=retrieved_at,
            content_hash=content_hash(raw),
            storage_path=str(cache_path),
        )
        return FetchResult(data=json.loads(raw), provenance=prov, raw_bytes=raw)

    # -- public API ---------------------------------------------------------
    def resolve_cik(self, ticker: str, use_cache: bool = True) -> str:
        """Map a ticker symbol to a zero-padded 10-digit CIK via company_tickers.json."""
        res = self._fetch_json(
            TICKERS_URL, "sec_company_tickers", "company_tickers", use_cache
        )
        want = ticker.strip().upper()
        for row in res.data.values():
            if str(row.get("ticker", "")).upper() == want:
                return normalize_cik(row["cik_str"])
        raise SECError(f"ticker {ticker!r} not found in SEC company_tickers.json")

    def fetch_submissions(self, cik: str, use_cache: bool = True) -> FetchResult:
        c = normalize_cik(cik)
        return self._fetch_json(
            SUBMISSIONS_URL.format(cik=c), "sec_submissions", f"submissions_{c}", use_cache
        )

    def fetch_companyfacts(self, cik: str, use_cache: bool = True) -> FetchResult:
        c = normalize_cik(cik)
        return self._fetch_json(
            COMPANYFACTS_URL.format(cik=c), "sec_companyfacts", f"companyfacts_{c}", use_cache
        )

    def fetch_filing_document(self, cik: str, accession_number: str, primary_doc: str, use_cache: bool = True) -> FetchResult:
        c = normalize_cik(cik)
        acc_no_hyphens = accession_number.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{c}/{acc_no_hyphens}/{primary_doc}"
        cache_key = f"{c}_{accession_number}_{primary_doc}"
        extension = primary_doc.split('.')[-1] if '.' in primary_doc else "txt"
        return self._fetch_raw(url, cache_key, extension, use_cache)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SECClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# --- parsing helpers (pure; operate on fetched JSON) -----------------------

def parse_company_meta(submissions: dict[str, Any]) -> dict[str, Any]:
    """Extract company-level fields from a submissions payload."""
    return {
        "cik": normalize_cik(submissions.get("cik", "0")),
        "name": submissions.get("name"),
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "tickers": submissions.get("tickers", []) or [],
        "exchanges": submissions.get("exchanges", []) or [],
        "country": (submissions.get("addresses", {}) or {})
        .get("business", {})
        .get("stateOrCountry"),
    }


def parse_recent_filings(
    submissions: dict[str, Any], forms: tuple[str, ...] | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    """Flatten submissions.filings.recent (columnar) into a list of filing dicts.

    Optionally filter to ``forms`` (e.g. ('10-K','10-Q','8-K')) and cap to ``limit``.
    """
    recent = (submissions.get("filings", {}) or {}).get("recent", {}) or {}
    accession = recent.get("accessionNumber", []) or []
    out: list[dict[str, Any]] = []
    for i in range(len(accession)):
        form = (recent.get("form", []) or [None])[i] if i < len(recent.get("form", [])) else None
        if forms and form not in forms:
            continue
        out.append(
            {
                "accession_number": accession[i],
                "form_type": form,
                "filing_date": _at(recent, "filingDate", i),
                "period_of_report": _at(recent, "reportDate", i),
                "primary_doc": _at(recent, "primaryDocument", i),
                "primary_doc_description": _at(recent, "primaryDocDescription", i),
            }
        )
        if limit and len(out) >= limit:
            break
    return out


def parse_facts(companyfacts: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    """Flatten companyfacts into individual datapoints.

    Each XBRL concept holds units -> list of period datapoints. We emit one dict
    per datapoint with taxonomy/concept/unit/value/period/form/accession.
    """
    out: list[dict[str, Any]] = []
    facts = companyfacts.get("facts", {}) or {}
    for taxonomy, concepts in facts.items():
        for concept, body in (concepts or {}).items():
            units = (body or {}).get("units", {}) or {}
            for unit, points in units.items():
                for p in points or []:
                    if p.get("val") is None or p.get("end") is None:
                        continue
                    out.append(
                        {
                            "taxonomy": taxonomy,
                            "concept": concept,
                            "unit": unit,
                            "value": p.get("val"),
                            "period_start": p.get("start"),
                            "period_end": p.get("end"),
                            "fiscal_year": p.get("fy"),
                            "fiscal_period": p.get("fp"),
                            "form": p.get("form"),
                            "filed": p.get("filed"),
                            "frame": p.get("frame"),
                            "accession_number": p.get("accn"),
                        }
                    )
                    if limit and len(out) >= limit:
                        return out
    return out


def _at(cols: dict[str, Any], key: str, i: int) -> Any:
    seq = cols.get(key, []) or []
    return seq[i] if i < len(seq) else None
