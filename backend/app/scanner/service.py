"""Scanner service — reads scorecards, builds + persists the ranked snapshot.

Thin I/O layer over ``ranking.py``. The scanner ranks whatever the *freshest*
valuation scorecards are; regenerating those scorecards (the heavy data refresh)
remains a separate pipeline. A background loop (see ``app/main.py``) rebuilds the
snapshot on an interval so the scan stays current.
"""
from __future__ import annotations

import glob
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.core.config import PROJECT_ROOT
from app.scanner.ranking import WEIGHTS, rank_universe

logger = logging.getLogger("asterion.scanner")

REPORTS_DIR = PROJECT_ROOT / "reports"
SNAPSHOT_PATH = REPORTS_DIR / "scanner_snapshot.json"

DISCLAIMER = (
    "Research candidates ranked by deterministic scores. Not investment advice "
    "and not a buy/sell recommendation. Each row links to its underlying "
    "evidence; confidence drops when inputs are missing."
)


def load_scorecards() -> list[dict[str, Any]]:
    """Load every valuation scorecard in the reports directory."""
    cards: list[dict[str, Any]] = []
    for path in sorted(glob.glob(str(REPORTS_DIR / "*_valuation_scorecard.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                cards.append(json.load(fh))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("scanner: skipping unreadable scorecard %s (%s)", path, exc)
    return cards


def build_snapshot() -> dict[str, Any]:
    """Build the ranked opportunity snapshot from the current scorecards."""
    cards = load_scorecards()
    opps = rank_universe(cards)
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universe": len(opps),
        "source": "valuation_scorecards",
        "disclaimer": DISCLAIMER,
        "weights": WEIGHTS,
        "opportunities": [o.as_dict() for o in opps],
    }


def write_snapshot(snapshot: dict[str, Any]) -> None:
    """Persist the snapshot to reports/scanner_snapshot.json (gitignored)."""
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=2)
    except OSError as exc:
        logger.warning("scanner: could not write snapshot (%s)", exc)


def refresh_snapshot() -> dict[str, Any]:
    """Build and persist a fresh snapshot. Returns it."""
    snap = build_snapshot()
    write_snapshot(snap)
    logger.info("scanner: refreshed %d opportunities at %s", snap["universe"], snap["as_of"])
    return snap


def get_opportunities() -> dict[str, Any]:
    """Live snapshot for the API (cheap for a small universe)."""
    return build_snapshot()


# ── scheduler config (env, no new deps) ────────────────────────────────────
def scanner_enabled() -> bool:
    return os.getenv("ASTERION_SCANNER_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def refresh_interval_seconds() -> int:
    try:
        minutes = float(os.getenv("ASTERION_SCANNER_REFRESH_MIN", "30"))
    except ValueError:
        minutes = 30.0
    return max(60, int(minutes * 60))  # floor 1 min
