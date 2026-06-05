"""FRED macro provider — risk-free rate from the 10Y Treasury (series DGS10).

Phase B of the dynamic-WACC stack. CAPM needs a risk-free rate; Phase A used a
static 4.5%. Here we pull the 10-Year constant-maturity Treasury yield from FRED
and use it instead, cached on disk so the scorecard / backtest scripts don't
re-hit the API on every ticker.

Honesty contract (same as the rest of the valuation stack):
  - If ``FRED_API_KEY`` is missing or the call fails → fall back to the static
    default and label the source ``fallback`` (never silently pretend it's live).
  - The API key is never logged and never returned to any caller.

Cache: ``data/cache/macro.json`` (12h TTL). Disk-based because the scorecard
generators run as one-shot scripts, so an in-process cache would not persist.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from app.core.config import PROJECT_ROOT, get_settings

log = logging.getLogger(__name__)

FRED_SERIES = "DGS10"  # 10Y constant-maturity Treasury, percent, daily
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

DEFAULT_RISK_FREE_RATE = 0.045  # static fallback, mirrors valuation.wacc
_CACHE_TTL_S = 12 * 3600
_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "macro.json"

# Sanity band for the 10Y yield. Outside this, treat the read as bad and fall back.
_RF_MIN, _RF_MAX = 0.001, 0.20


@dataclass
class MacroResult:
    risk_free_rate: float
    source: str          # "fred:DGS10" | "fred_cache:DGS10" | "fallback"
    as_of: str | None    # observation date (YYYY-MM-DD) or None for fallback
    series_id: str = FRED_SERIES

    def as_dict(self) -> dict:
        return {
            "risk_free_rate": self.risk_free_rate,
            "source": self.source,
            "as_of": self.as_of,
            "series_id": self.series_id,
        }


def _read_cache() -> MacroResult | None:
    try:
        raw = json.loads(_CACHE_PATH.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return None
    if time.time() - raw.get("_cached_at", 0) > _CACHE_TTL_S:
        return None
    rate = raw.get("risk_free_rate")
    if not isinstance(rate, (int, float)) or not (_RF_MIN <= rate <= _RF_MAX):
        return None
    return MacroResult(
        risk_free_rate=float(rate),
        source="fred_cache:DGS10",
        as_of=raw.get("as_of"),
    )


def _write_cache(rate: float, as_of: str | None) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps({
            "risk_free_rate": rate,
            "as_of": as_of,
            "series_id": FRED_SERIES,
            "_cached_at": time.time(),
        }, indent=2))
    except OSError as exc:  # cache is best-effort
        log.debug("macro cache write failed: %s", exc)


def _fetch_fred(api_key: str) -> MacroResult | None:
    """Latest valid DGS10 observation as a decimal rate, or None on any failure."""
    try:
        res = requests.get(
            FRED_BASE,
            params={
                "series_id": FRED_SERIES,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 10,  # last few days; weekends/holidays come back as "."
            },
            timeout=8,
        )
    except requests.RequestException as exc:
        log.warning("FRED request failed: %s", exc)
        return None
    if res.status_code != 200:
        log.warning("FRED returned HTTP %s", res.status_code)
        return None
    try:
        observations = res.json().get("observations", [])
    except ValueError:
        return None
    for obs in observations:  # newest first
        val = obs.get("value")
        if val in (None, ".", ""):
            continue
        try:
            pct = float(val)
        except (TypeError, ValueError):
            continue
        rate = pct / 100.0  # FRED reports percent
        if not (_RF_MIN <= rate <= _RF_MAX):
            continue
        as_of = obs.get("date")
        _write_cache(rate, as_of)
        return MacroResult(risk_free_rate=rate, source="fred:DGS10", as_of=as_of)
    return None


def get_risk_free_rate(*, force_refresh: bool = False) -> MacroResult:
    """Risk-free rate for CAPM, FRED-sourced when possible.

    Order: fresh disk cache → live FRED (if key present) → static fallback.
    Always returns a usable result; ``source`` records provenance honestly.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            return cached

    api_key = get_settings().fred_api_key
    if api_key:
        live = _fetch_fred(api_key)
        if live is not None:
            return live
        # live failed — try a stale cache before the static fallback
        stale = _read_cache()
        if stale is not None:
            return stale

    return MacroResult(
        risk_free_rate=DEFAULT_RISK_FREE_RATE,
        source="fallback",
        as_of=None,
    )


def fred_configured() -> bool:
    return bool(get_settings().fred_api_key)
