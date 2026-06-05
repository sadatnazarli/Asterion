"""IPO-mode API — serve persisted IPO scorecards (read-only). No buy/sell."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ipo import service

router = APIRouter()


@router.get("/{ticker}")
def get_ipo_scorecard(ticker: str):
    """Return the persisted IPO scorecard JSON for a candidate (e.g. SPACEX)."""
    data = service.load_ipo_scorecard(ticker)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No IPO scorecard for {ticker.upper()}. "
                   f"Run scripts/analyze_ipo_candidate.py {ticker.upper()} first.",
        )
    return data
