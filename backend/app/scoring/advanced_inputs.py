"""Advanced-score input fetcher.

M10: the previous implementation returned HARDCODED CONSTANTS for every ticker
(a fixed gross margin, revenue growth, current ratio, etc.), which made every
company's advanced scores identical. That mock behaviour is REMOVED. Real
per-ticker inputs are now
built by ``app.scoring.real_inputs.build_advanced_inputs`` from SEC facts +
reverse-DCF + price history. When no DB connection is provided this returns an
empty dict with an explicit ``_missing`` marker — it never fabricates values.
"""
from __future__ import annotations

from typing import Any, Dict

from app.scoring.real_inputs import build_advanced_inputs


class AdvancedInputsFetcher:
    """Thin wrapper over real_inputs. No mock constants."""

    def __init__(self, db_session=None):
        self.db_session = db_session

    def fetch_all_inputs(
        self,
        ticker: str,
        *,
        company_id: int | None = None,
        price_history: list[float] | None = None,
        market_cap: float | None = None,
    ) -> Dict[str, Any]:
        """Return real advanced-score inputs, or an empty dict with a missing flag.

        Requires a DB connection (``self.db_session``) and ``company_id``. Without
        them we cannot compute anything real, so we return nothing rather than
        inventing numbers.
        """
        if self.db_session is None or company_id is None:
            return {"_missing": ["no_db_connection_or_company_id"]}
        inputs, missing = build_advanced_inputs(
            self.db_session, company_id, ticker,
            price_history=price_history, market_cap=market_cap,
        )
        inputs = dict(inputs)
        inputs["_missing"] = missing
        return inputs
