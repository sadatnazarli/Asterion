"""Beta provider — live levered beta from FMP, with a sector fallback.

Phase B of the dynamic-WACC stack. Phase A bucketed beta by sector/theme
(``valuation.wacc.beta_for_symbol``). Here, if an ``FMP_API_KEY`` is configured,
we use FMP's company-profile beta; otherwise we keep the deterministic sector
fallback. The beta *source* is always recorded so a scorecard reader can tell a
provider beta from a sector guess:

  - ``provider_beta:fmp``        — live beta from FMP
  - ``sector_fallback:<theme>``  — Phase-A theme beta (no provider / call failed)
  - ``default``                  — unmapped symbol, generic 1.10

Honesty contract: the API key is never logged or returned. A missing key or a
failed/implausible response degrades cleanly to the sector fallback.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from app.core.config import PROJECT_ROOT, get_settings
from app.valuation.wacc import beta_for_symbol

log = logging.getLogger(__name__)

FMP_PROFILE_BASE = "https://financialmodelingprep.com/api/v3/profile"

_CACHE_TTL_S = 24 * 3600
_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "beta.json"

# Plausible levered-beta band; outside this the provider value is rejected.
_BETA_MIN, _BETA_MAX = 0.1, 4.0


@dataclass
class BetaResult:
    beta: float
    source: str   # "provider_beta:fmp" | "sector_fallback:<theme>" | "default"

    def as_dict(self) -> dict:
        return {"beta": self.beta, "source": self.source}


def _read_cache() -> dict:
    try:
        raw = json.loads(_CACHE_PATH.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return {}
    if time.time() - raw.get("_cached_at", 0) > _CACHE_TTL_S:
        return {}
    entries = raw.get("betas")
    return entries if isinstance(entries, dict) else {}


def _write_cache(symbol: str, beta: float) -> None:
    try:
        existing = {}
        if _CACHE_PATH.exists():
            try:
                existing = json.loads(_CACHE_PATH.read_text()).get("betas", {}) or {}
            except (ValueError, OSError):
                existing = {}
        existing[symbol.upper()] = beta
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(
            {"betas": existing, "_cached_at": time.time()}, indent=2,
        ))
    except OSError as exc:  # best-effort
        log.debug("beta cache write failed: %s", exc)


def _fetch_fmp_beta(symbol: str, api_key: str) -> float | None:
    try:
        res = requests.get(
            f"{FMP_PROFILE_BASE}/{symbol.upper()}",
            params={"apikey": api_key},
            timeout=8,
        )
    except requests.RequestException as exc:
        log.warning("FMP beta request failed for %s: %s", symbol, exc)
        return None
    if res.status_code != 200:
        log.warning("FMP beta returned HTTP %s for %s", res.status_code, symbol)
        return None
    try:
        data = res.json()
    except ValueError:
        return None
    if not isinstance(data, list) or not data:
        return None
    beta = data[0].get("beta")
    try:
        beta = float(beta)
    except (TypeError, ValueError):
        return None
    if not (_BETA_MIN <= beta <= _BETA_MAX):
        return None
    return beta


def get_beta(symbol: str) -> BetaResult:
    """Levered beta for *symbol* — FMP when configured, else sector fallback."""
    sym = symbol.upper()

    cache = _read_cache()
    if sym in cache and isinstance(cache[sym], (int, float)):
        return BetaResult(beta=float(cache[sym]), source="provider_beta:fmp")

    api_key = get_settings().fmp_api_key
    if api_key:
        live = _fetch_fmp_beta(sym, api_key)
        if live is not None:
            _write_cache(sym, live)
            return BetaResult(beta=live, source="provider_beta:fmp")

    beta, source = beta_for_symbol(sym)
    return BetaResult(beta=beta, source=source)


def fmp_configured() -> bool:
    return bool(get_settings().fmp_api_key)
