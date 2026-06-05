"""Official-source verification (Phase 1) + S-1 parsing (Phase 3).

Two layers, deliberately separated so the heavy I/O stays out of the unit tests:

- ``verify_sec_registrant`` / ``fetch_filing_text`` — network I/O against SEC
  EDGAR (rate-limited, SEC ``User-Agent`` required).
- ``parse_filing_text`` — PURE. Labeled-pattern extraction over already-fetched
  text. Every number it returns carries a provenance snippet and a confidence.

Extraction is regex/label based (an S-1's financials live in HTML tables, not in
machine-readable XBRL for a first-time registrant), so confidence is capped below
1.0 and the source snippet is always retained for audit. Nothing is invented: a
figure the patterns can't find is recorded in ``missing``.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.ipo.schemas import (
    VERIFICATION_FOUND,
    VERIFICATION_NONE,
    FilingFact,
    FilingFacts,
    Provenance,
    VerificationResult,
)

try:  # SEC requires a descriptive UA; reuse Asterion's configured one.
    from app.core.config import settings

    _UA = settings.sec_user_agent
except Exception:  # pragma: no cover - config optional in pure-test contexts
    _UA = "Asterion Research (set-your-email@example.com)"

_EDGAR_FTS = "https://efts.sec.gov/LATEST/search-index"
_EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
_EDGAR_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

_IPO_FORMS = ("S-1", "S-1/A", "424B1", "424B2", "424B3", "424B4", "424B5", "F-1", "F-1/A")


# ── HTTP helpers ────────────────────────────────────────────────────────────
def _http_get(url: str, *, accept: str = "application/json") -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted SEC host)
        return resp.read().decode("utf-8", errors="ignore")


def _http_get_json(url: str) -> Any:
    return json.loads(_http_get(url))


def detag(html: str) -> str:
    """Strip HTML to whitespace-collapsed text (good enough for labeled search)."""
    t = re.sub(r"<[^>]+>", " ", html)
    repl = {
        "&#160;": " ", "&nbsp;": " ", "&amp;": "&",
        "&#8217;": "'", "&#8216;": "'", "&#8220;": '"', "&#8221;": '"',
        "&#59;": ";", "&#58;": ":", "&#8226;": "-", "&#38;": "&",
    }
    for k, v in repl.items():
        t = t.replace(k, v)
    return re.sub(r"\s+", " ", t).strip()


# ── Phase 1: official-source verification ───────────────────────────────────
def find_cik(name: str) -> str | None:
    """Resolve a CIK from a company name via EDGAR full-text search."""
    url = f"{_EDGAR_FTS}?{urllib.parse.urlencode({'q': f'\"{name}\"', 'forms': 'S-1'})}"
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, ValueError):
        return None
    for hit in (data.get("hits", {}) or {}).get("hits", []):
        ciks = (hit.get("_source", {}) or {}).get("ciks") or []
        if ciks:
            return str(ciks[0]).lstrip("0").zfill(10)
    return None


def verify_sec_registrant(
    name: str, *, ticker: str | None = None, cik: str | None = None,
) -> VerificationResult:
    """Phase 1 — check SEC EDGAR for an official IPO registration filing.

    Returns a :class:`VerificationResult`. ``status`` is ``official_filing_found``
    only when at least one S-1 / F-1 / 424B filing is present for the registrant.
    """
    sources = [
        "SEC EDGAR full-text search (efts.sec.gov)",
        "SEC EDGAR submissions API (data.sec.gov)",
    ]
    res = VerificationResult(query=name, status=VERIFICATION_NONE, sources_checked=sources)

    cik10 = (cik.lstrip("0").zfill(10) if cik else None) or find_cik(name)
    if not cik10:
        res.notes.append("No matching SEC registrant found via EDGAR full-text search.")
        return res

    try:
        sub = _http_get_json(_EDGAR_SUBMISSIONS.format(cik=cik10))
    except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        res.notes.append(f"EDGAR submissions API unreachable: {exc}")
        return res

    res.registrant_name = sub.get("name")
    res.cik = cik10
    tickers = sub.get("tickers") or []
    res.proposed_ticker = (ticker or (tickers[0] if tickers else None))

    recent = (sub.get("filings", {}) or {}).get("recent", {}) or {}
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    for i, form in enumerate(forms):
        if form in _IPO_FORMS:
            acc = accs[i] if i < len(accs) else ""
            doc = docs[i] if i < len(docs) else ""
            url = _EDGAR_ARCHIVE.format(
                cik=int(cik10), acc_nodash=acc.replace("-", ""), doc=doc,
            ) if acc and doc else None
            res.filings.append({
                "form": form,
                "filing_date": dates[i] if i < len(dates) else None,
                "accession": acc,
                "document": doc,
                "url": url,
            })

    if res.filings:
        res.status = VERIFICATION_FOUND
        res.notes.append(
            f"Official registration filing(s) found for {res.registrant_name} "
            f"(CIK {cik10}): {', '.join(sorted({f['form'] for f in res.filings}))}."
        )
    else:
        res.notes.append(
            f"Registrant {res.registrant_name} exists but no S-1/F-1/424B IPO filing found."
        )
    return res


def fetch_filing_text(url: str) -> str:
    """Download a filing document and return detagged text. SEC UA required."""
    return detag(_http_get(url, accept="text/html"))


# ── Phase 3: S-1 / prospectus parsing (PURE) ────────────────────────────────
_NUM = r"\$?\(?([\d][\d,]*)\)?"


def _money_m(s: str) -> float:
    """'$18,674' / '(2,589)' (millions) -> float millions (loss kept positive sign by caller)."""
    return float(s.replace(",", "").replace("$", "").replace("(", "").replace(")", ""))


def _snip(text: str, idx: int, width: int = 160) -> str:
    lo = max(0, idx - 20)
    return text[lo: idx + width].strip()


def _find(text: str, pattern: str, flags: int = re.IGNORECASE) -> re.Match | None:
    return re.search(pattern, text, flags)


def parse_filing_text(text: str, *, ticker: str, source_url: str | None = None) -> FilingFacts:
    """Extract structured filing facts from detagged S-1 text. Pure + deterministic.

    Records every found number as a :class:`FilingFact` with a snippet; anything
    not found lands in ``missing`` (never guessed).
    """
    facts = FilingFacts(ticker=ticker.upper(), source_url=source_url)

    def add(key, value, unit, period, snippet, conf):
        facts.add(FilingFact(
            key=key, value=value, unit=unit, period=period,
            provenance=Provenance(source_url=source_url, section=None, snippet=snippet, confidence=conf),
        ))

    # IPO price per share
    m = _find(text, r"initial public offering price (?:to be|of) \$([\d.]+) per share")
    add("ipo_price_per_share", float(m.group(1)) if m else None, "per_share",
        None, _snip(text, m.start()) if m else None, 0.95 if m else 0.0)

    # Shares offered (Class A)
    m = _find(text, r"offering ([\d,]+) shares of (?:our )?Class A common stock")
    add("shares_offered", _money_m(m.group(1)) if m else None, "shares",
        None, _snip(text, m.start()) if m else None, 0.92 if m else 0.0)

    # Shares outstanding by class (pre-offering)
    m = _find(text, r"([\d,]+) shares of Class A common stock and ([\d,]+) shares of Class B "
                    r"common stock outstanding as of")
    if m:
        a = _money_m(m.group(1)); b = _money_m(m.group(2))
        add("class_a_shares_outstanding", a, "shares", "as_of_period_end", _snip(text, m.start()), 0.9)
        add("class_b_shares_outstanding", b, "shares", "as_of_period_end", _snip(text, m.start()), 0.9)
        add("total_shares_pre_offering", a + b, "shares", "as_of_period_end", _snip(text, m.start()), 0.88)
    else:
        for k in ("class_a_shares_outstanding", "class_b_shares_outstanding", "total_shares_pre_offering"):
            add(k, None, "shares", None, None, 0.0)

    # Cash & equivalents
    m = _find(text, r"cash and cash equivalents of \$([\d,]+) million as of")
    add("cash_and_equivalents", _money_m(m.group(1)) if m else None, "usd_millions",
        "as_of_period_end", _snip(text, m.start()) if m else None, 0.9 if m else 0.0)

    # Summary financials: revenue + loss-from-operations (+ adj EBITDA) triples,
    # with a nearby period anchor.
    triple = re.compile(
        r"(?:basis of|revenue of) \$([\d,]+) million,? (?:and a )?loss from operations of "
        r"\$\(([\d,]+)\) million(?:,? and (?:Segment )?Adjusted EBITDA of \$\(?([\d,]+)\)? million)?",
        re.IGNORECASE,
    )
    found_periods: set[str] = set()
    for mt in triple.finditer(text):
        ctx = text[max(0, mt.start() - 160): mt.start()].lower()
        if "three months" in ctx or "march 31, 2026" in ctx:
            period = "Q1-2026"
        elif "year ended" in ctx or " 2025" in ctx or "fiscal 2025" in ctx:
            period = "FY2025"
        else:
            # magnitude fallback: a full year out-revenues a single quarter
            period = "FY2025" if _money_m(mt.group(1)) > 10000 else "Q1-2026"
        if period in found_periods:
            continue
        found_periods.add(period)
        suf = "fy2025" if period == "FY2025" else "q1_2026"
        snip = _snip(text, mt.start())
        add(f"revenue_{suf}", _money_m(mt.group(1)), "usd_millions", period, snip, 0.9)
        add(f"loss_from_operations_{suf}", -_money_m(mt.group(2)), "usd_millions", period, snip, 0.9)
        if mt.group(3):
            add(f"adjusted_ebitda_{suf}", _money_m(mt.group(3)), "usd_millions", period, snip, 0.85)
    for need in ("revenue_fy2025", "loss_from_operations_fy2025", "revenue_q1_2026"):
        if need not in facts.facts:
            add(need, None, "usd_millions", None, None, 0.0)

    # Voting structure
    has_super = bool(_find(text, r"Class B common stock will have ten votes per share"))
    add("class_b_votes_per_share", 10.0 if has_super else None, "ratio", None,
        "Class B common stock will have ten votes per share" if has_super else None,
        0.9 if has_super else 0.0)
    add("class_a_votes_per_share",
        1.0 if _find(text, r"Class A common stock will have one vote") or has_super else None,
        "ratio", None, None, 0.9 if has_super else 0.0)

    # Lock-up — prefer a "NNN days ... prospectus" match whose context mentions
    # "lock-up" (the doc has other unrelated "NN days ... prospectus" phrases).
    lk_m = None
    for cand in re.finditer(r"(\d{2,3}) days (?:from|after) the date of this prospectus", text, re.I):
        ctx = text[max(0, cand.start() - 200): cand.end() + 60].lower()
        if "lock" in ctx:
            lk_m = cand
            break
        lk_m = lk_m or cand  # fallback to first if none mention lock-up
    add("lockup_days", float(lk_m.group(1)) if lk_m else None, "days",
        None, _snip(text, lk_m.start(), 90) if lk_m else None, 0.85 if lk_m else 0.0)

    return facts
