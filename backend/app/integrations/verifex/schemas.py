"""Verifex adapter data shapes. Provider-shaped, no Asterion logic here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Adapter-level status (see docs/30 §5):
#   ok                   provider answered, >= 1 match
#   no_match             provider answered, zero matches  (NOT "clean")
#   provider_unavailable key/URL missing, or request never reached the provider
#   error                provider reached but response unusable
OK = "ok"
NO_MATCH = "no_match"
PROVIDER_UNAVAILABLE = "provider_unavailable"
ERROR = "error"


@dataclass
class VerifexMatch:
    name: str
    match_score: float | None       # 0-1 provider confidence, if given
    categories: list[str]           # raw provider category tags
    country: str | None = None
    source: str | None = None       # which list/source the hit came from
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "match_score": self.match_score,
            "categories": self.categories,
            "country": self.country,
            "source": self.source,
        }


@dataclass
class VerifexScreenResult:
    status: str                     # ok|no_match|provider_unavailable|error
    query: str
    matches: list[VerifexMatch] = field(default_factory=list)
    raw: dict[str, Any] | None = None   # provider payload (no secrets)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "matches": [m.as_dict() for m in self.matches],
            "notes": self.notes,
        }
