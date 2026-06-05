"""Decision-intelligence API — serve persisted decision reports (read-only).

Research only. No buy/sell. Merges Asterion financial risk + Verifex compliance
risk; see docs/30. Reports are produced by scripts/generate_decision_report.py.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.decision_intelligence import service

router = APIRouter()


@router.get("/{entity}")
def get_decision_report(entity: str):
    """Return the persisted decision-intelligence report for an entity.

    ``entity`` is a public ticker (e.g. META) or a known key/slug (e.g. SPACEX).
    """
    data = service.load_decision_report(entity)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No decision report for {entity}. Run "
                f"scripts/generate_decision_report.py {entity} first."
            ),
        )
    return data
