"""Opportunity Scanner API (M13a).

Serves the ranked, deterministic screen of the ingested universe. Research
candidates with evidence links — never buy/sell advice.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.scanner.service import get_opportunities

router = APIRouter()


@router.get("/opportunities")
def opportunities() -> dict:
    """Ranked opportunity screen over the current universe (live)."""
    return get_opportunities()
