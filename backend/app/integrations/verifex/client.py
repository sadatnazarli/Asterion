"""Verifex HTTP client. Stdlib only, fully isolated, secret-safe.

The real Verifex endpoint + schema are not yet confirmed (docs/30 §5). This ships
the request/parse seam: it makes a live call only when *both* a key and a base
URL are configured, times out fast, and swallows every error into a
``provider_unavailable`` / ``error`` result so it can never block the app. The
API key is read from config and sent in the Authorization header only — it is
never logged, printed, or returned in any result.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings
from app.integrations.verifex import mapper
from app.integrations.verifex.schemas import (
    ERROR,
    PROVIDER_UNAVAILABLE,
    VerifexScreenResult,
)

logger = logging.getLogger("asterion.verifex")

_TIMEOUT_SECONDS = 8
# Endpoint path under the configured base URL. Path-only so no production host is
# hardcoded; override-able if the real route differs.
_SCREEN_PATH = "/v1/screen"


def _unavailable(query: str, note: str) -> VerifexScreenResult:
    return VerifexScreenResult(status=PROVIDER_UNAVAILABLE, query=query, notes=note)


def screen_entity(
    name: str,
    *,
    country: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: int = _TIMEOUT_SECONDS,
) -> VerifexScreenResult:
    """Screen one legal entity by name. Never raises.

    Returns a ``provider_unavailable`` result when the key or base URL is missing
    or the request fails, and an ``error`` result when the provider responds with
    something unusable. ``api_key`` / ``base_url`` default to config and are only
    parameters here for testing; the key is never logged.
    """
    query = (name or "").strip()
    if not query:
        return _unavailable(query, "empty entity name")

    key = api_key if api_key is not None else settings.verifex_api_key
    url_base = base_url if base_url is not None else settings.verifex_api_base_url
    if not key or not url_base:
        return _unavailable(query, "Verifex not configured (key and/or base URL missing).")

    endpoint = url_base.rstrip("/") + _SCREEN_PATH
    body = json.dumps({"name": query, "country": country}).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"Bearer {key}")  # secret stays in the header

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Log status only — never the key, never the full request.
        logger.warning("verifex: HTTP %s screening entity", exc.code)
        return VerifexScreenResult(status=ERROR, query=query, notes=f"provider HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("verifex: screen failed (%s)", type(exc).__name__)
        return _unavailable(query, f"request failed: {type(exc).__name__}")

    return mapper.parse_provider_payload(payload, query=query)
