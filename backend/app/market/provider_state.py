"""Track last successful provider calls for /api/system/providers."""
from __future__ import annotations

from datetime import UTC, datetime

_finnhub_last_success_at: str | None = None


def record_finnhub_success() -> None:
    global _finnhub_last_success_at
    _finnhub_last_success_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")


def finnhub_last_success_at() -> str | None:
    return _finnhub_last_success_at
