"""Scoring inputs orchestrator — fetches SEC facts, calls pure formulas, stores results.

This is the bridge between the DB (financial_facts) and the pure formula
functions in app.quant.fundamentals / forensic.  No LLM — every number is
deterministic and reproducible from the raw XBRL facts.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.quant.fundamentals import (
    FormulaResult,
    revenue_growth,
    gross_margin,
    operating_margin,
    net_margin,
    free_cash_flow_margin,
    return_on_equity,
    return_on_assets,
    current_ratio,
    debt_to_equity,
    sbc_to_revenue,
    sbc_to_operating_cash_flow,
    shares_outstanding_change,
)
from app.quant.forensic import (
    altman_z_score,
    piotroski_f_score,
    accruals_ratio,
    quality_of_earnings,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Concept fallback chains — ordered by most-common XBRL tag first.
# Each key maps to the list of XBRL concepts to try (first match wins).
# ---------------------------------------------------------------------------
_CONCEPT_CHAINS: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    # Capex = cash outflow for productive assets. M11: broadened so NVDA/Visa
    # (which tag PaymentsToAcquireProductiveAssets, not the PP&E concept) get a
    # real FCF. Acquisitions (PaymentsToAcquireBusinessesNetOfCashAcquired) are
    # deliberately EXCLUDED — they are M&A, not maintenance/growth capex.
    # CapitalExpendituresIncurredButNotYetPaid is an accrual disclosure, not a
    # cash outflow, so it is excluded too.
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PurchasesOfPropertyAndEquipmentAndCapitalizedSoftware",
        "PaymentsForCapitalImprovements",
        "CapitalExpenditure",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestExpenseNonoperating",
        "InterestAndDebtExpense",
    ],
    "income_tax_expense": ["IncomeTaxExpenseBenefit"],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterest",
    ],
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_liabilities": ["Liabilities"],
    "shareholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "total_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "DebtCurrent",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "sbc": [
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
    ],
    "long_term_debt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ],
}

# Shares outstanding lives in multiple taxonomies / units.
_SHARES_CONCEPTS_DEI: list[str] = ["EntityCommonStockSharesOutstanding"]
_SHARES_CONCEPTS_GAAP: list[str] = [
    "CommonStockSharesOutstanding",
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
]

# Date window used to fuzzy-match fiscal period ends (±15 days).
_DATE_WINDOW_DAYS = 15


# ── 1. Low-level fact fetchers ─────────────────────────────────────────────

def get_fact_value(
    conn: psycopg.Connection,
    company_id: int,
    concepts: list[str],
    period_end: date,
    *,
    fiscal_period: str | None = None,
    unit: str = "USD",
) -> tuple[float | None, int | None]:
    """Return ``(value, fact_id)`` for the first matching XBRL concept.

    Tries each concept in *concepts* order against *financial_facts*.
    A ±15-day window around *period_end* accommodates fiscal-year-end
    alignment differences across filings.  When *fiscal_period* is supplied
    it is used as an additional filter.
    """
    lo = period_end - timedelta(days=_DATE_WINDOW_DAYS)
    hi = period_end + timedelta(days=_DATE_WINDOW_DAYS)

    for concept in concepts:
        if fiscal_period is not None:
            row = conn.execute(
                """
                SELECT id, value
                  FROM financial_facts
                 WHERE company_id = %s
                   AND concept    = %s
                   AND unit       = %s
                   AND fiscal_period = %s
                   AND period_end BETWEEN %s AND %s
                 ORDER BY period_end DESC, filed DESC
                 LIMIT 1
                """,
                (company_id, concept, unit, fiscal_period, lo, hi),
            ).fetchone()
            if row is not None:
                return (float(row[1]), int(row[0]))

        # Fallback: ignore fiscal_period — match by date window alone.
        row = conn.execute(
            """
            SELECT id, value
              FROM financial_facts
             WHERE company_id = %s
               AND concept    = %s
               AND unit       = %s
               AND period_end BETWEEN %s AND %s
             ORDER BY period_end DESC, filed DESC
             LIMIT 1
            """,
            (company_id, concept, unit, lo, hi),
        ).fetchone()
        if row is not None:
            return (float(row[1]), int(row[0]))

    return (None, None)


def get_fact_value_for_period(
    conn: psycopg.Connection,
    company_id: int,
    concepts: list[str],
    fiscal_year: int,
    fiscal_period: str,
    *,
    unit: str = "USD",
) -> tuple[float | None, int | None]:
    """Like :func:`get_fact_value` but matches on *fiscal_year* / *fiscal_period*."""
    for concept in concepts:
        row = conn.execute(
            """
            SELECT id, value
              FROM financial_facts
             WHERE company_id    = %s
               AND concept       = %s
               AND unit          = %s
               AND fiscal_year   = %s
               AND fiscal_period = %s
             ORDER BY filed DESC
             LIMIT 1
            """,
            (company_id, concept, unit, fiscal_year, fiscal_period),
        ).fetchone()
        if row is not None:
            return (float(row[1]), int(row[0]))

    return (None, None)


def detect_concept(
    conn: psycopg.Connection,
    company_id: int,
    concepts: list[str],
    period_end: date,
    *,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    unit: str = "USD",
) -> str | None:
    """Return WHICH concept in *concepts* produced a value for this period.

    Mirrors :func:`fetch_period_data`'s match order (fiscal_year/period first,
    then a ±15-day date window) so callers can record the exact XBRL source
    concept (provenance) consistently with the value that was actually used.
    """
    # Precise fiscal_year + period match first — same as get_fact_value_for_period.
    if fiscal_year is not None and fiscal_period is not None:
        for concept in concepts:
            row = conn.execute(
                """
                SELECT 1 FROM financial_facts
                 WHERE company_id = %s AND concept = %s AND unit = %s
                   AND fiscal_year = %s AND fiscal_period = %s
                 LIMIT 1
                """,
                (company_id, concept, unit, fiscal_year, fiscal_period),
            ).fetchone()
            if row is not None:
                return concept

    lo = period_end - timedelta(days=_DATE_WINDOW_DAYS)
    hi = period_end + timedelta(days=_DATE_WINDOW_DAYS)
    for concept in concepts:
        if fiscal_period is not None:
            row = conn.execute(
                """
                SELECT 1 FROM financial_facts
                 WHERE company_id = %s AND concept = %s AND unit = %s
                   AND fiscal_period = %s AND period_end BETWEEN %s AND %s
                 LIMIT 1
                """,
                (company_id, concept, unit, fiscal_period, lo, hi),
            ).fetchone()
            if row is not None:
                return concept
        row = conn.execute(
            """
            SELECT 1 FROM financial_facts
             WHERE company_id = %s AND concept = %s AND unit = %s
               AND period_end BETWEEN %s AND %s
             LIMIT 1
            """,
            (company_id, concept, unit, lo, hi),
        ).fetchone()
        if row is not None:
            return concept
    return None


# ── 2. Aggregate period data fetcher ───────────────────────────────────────

def _fetch_shares_outstanding(
    conn: psycopg.Connection,
    company_id: int,
    period_end: date,
    fiscal_period: str | None,
) -> tuple[float | None, int | None]:
    """Shares outstanding lives in *dei* and *us-gaap* taxonomies with unit='shares'."""
    # Try DEI taxonomy first (most authoritative for share count).
    val, fid = get_fact_value(
        conn, company_id, _SHARES_CONCEPTS_DEI, period_end,
        fiscal_period=fiscal_period, unit="shares",
    )
    if val is not None:
        return (val, fid)

    # Fallback to us-gaap concepts.
    return get_fact_value(
        conn, company_id, _SHARES_CONCEPTS_GAAP, period_end,
        fiscal_period=fiscal_period, unit="shares",
    )


def fetch_period_data(
    conn: psycopg.Connection,
    company_id: int,
    period_end: date,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
) -> dict[str, tuple[float | None, int | None]]:
    """Fetch ALL financial inputs for one reporting period.

    Returns a dict mapping metric name → ``(value, fact_id)``.
    """
    data: dict[str, tuple[float | None, int | None]] = {}

    for metric, concepts in _CONCEPT_CHAINS.items():
        # For fiscal_year-based lookup when both identifiers are available,
        # try the more precise approach first, then fall back to date-based.
        if fiscal_year is not None and fiscal_period is not None:
            val, fid = get_fact_value_for_period(
                conn, company_id, concepts, fiscal_year, fiscal_period,
            )
            if val is not None:
                data[metric] = (val, fid)
                continue

        data[metric] = get_fact_value(
            conn, company_id, concepts, period_end,
            fiscal_period=fiscal_period,
        )

    # Shares outstanding — special taxonomy / unit handling.
    data["shares_outstanding"] = _fetch_shares_outstanding(
        conn, company_id, period_end, fiscal_period,
    )

    return data


# ── 3. Compute all ratios ─────────────────────────────────────────────────

def _v(data: dict[str, tuple[float | None, int | None]], key: str) -> float | None:
    """Convenience: extract the *value* from a ``(value, fact_id)`` pair."""
    pair = data.get(key)
    return pair[0] if pair else None


def _safe_div_inline(a: float | None, b: float | None) -> float | None:
    """Safe division for computing derived ratios inline."""
    if a is None or b is None or b == 0.0:
        return None
    return a / b


def compute_all_ratios(
    conn: psycopg.Connection,
    company_id: int,
    period_end: date,
    prior_period_end: date | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
) -> list[FormulaResult]:
    """Fetch data for *period_end* (and optionally the prior period), then
    run every registered formula.  Returns a flat list of
    :class:`FormulaResult` objects.
    """
    cur = fetch_period_data(conn, company_id, period_end, fiscal_year, fiscal_period)

    prior: dict[str, tuple[float | None, int | None]] | None = None
    if prior_period_end is not None:
        prior_fy = (fiscal_year - 1) if fiscal_year else None
        prior = fetch_period_data(
            conn, company_id, prior_period_end, prior_fy, fiscal_period,
        )

    results: list[FormulaResult] = []

    # -- Fundamental single-period ratios -----------------------------------
    revenue = _v(cur, "revenue")
    gross_profit_val = _v(cur, "gross_profit")
    operating_income = _v(cur, "operating_income")
    net_income = _v(cur, "net_income")
    op_cf = _v(cur, "operating_cash_flow")
    capex = _v(cur, "capex")
    total_assets = _v(cur, "total_assets")
    current_assets = _v(cur, "current_assets")
    current_liabilities = _v(cur, "current_liabilities")
    total_liabilities = _v(cur, "total_liabilities")
    equity = _v(cur, "shareholders_equity")
    total_debt_val = _v(cur, "total_debt")
    sbc_val = _v(cur, "sbc")
    shares = _v(cur, "shares_outstanding")
    retained_earnings = _v(cur, "retained_earnings")
    cash_val = _v(cur, "cash")
    long_term_debt_val = _v(cur, "long_term_debt")

    # Derived metrics
    working_capital: float | None = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    # EBIT proxy = operating income
    ebit = operating_income

    results.append(gross_margin(gross_profit_val, revenue))
    results.append(operating_margin(operating_income, revenue))
    results.append(net_margin(net_income, revenue))
    results.append(free_cash_flow_margin(op_cf, capex, revenue))
    results.append(return_on_equity(net_income, equity))
    results.append(return_on_assets(net_income, total_assets))
    results.append(current_ratio(current_assets, current_liabilities))
    results.append(debt_to_equity(total_debt_val, equity))
    results.append(sbc_to_revenue(sbc_val, revenue))
    results.append(sbc_to_operating_cash_flow(sbc_val, op_cf))

    # -- Revenue growth & share dilution (need prior period) ----------------
    if prior is not None:
        prior_revenue = _v(prior, "revenue")
        results.append(revenue_growth(revenue, prior_revenue))

        prior_shares = _v(prior, "shares_outstanding")
        results.append(shares_outstanding_change(shares, prior_shares))
    else:
        # Still emit a result with missing flags so consumers see it.
        results.append(revenue_growth(revenue, None))
        results.append(shares_outstanding_change(shares, None))

    # -- Forensic ratios ----------------------------------------------------
    results.append(accruals_ratio(net_income, op_cf, total_assets))
    results.append(quality_of_earnings(op_cf, net_income))

    # Altman Z-Score needs several balance-sheet / income items.
    results.append(
        altman_z_score(
            working_capital=working_capital,
            total_assets=total_assets,
            retained_earnings=retained_earnings,
            ebit=ebit,
            market_cap=equity,      # book equity as proxy when market cap unavailable
            total_liabilities=total_liabilities,
            revenue=revenue,
        )
    )

    # Piotroski F-Score requires both periods.
    if prior is not None:
        prior_total_assets = _v(prior, "total_assets")
        prior_current_liabilities = _v(prior, "current_liabilities")
        prior_current_assets = _v(prior, "current_assets")
        prior_long_term_debt = _v(prior, "long_term_debt")
        prior_net_income = _v(prior, "net_income")
        prior_revenue = _v(prior, "revenue")
        prior_gross_profit = _v(prior, "gross_profit")
        prior_op_cf = _v(prior, "operating_cash_flow")
        prior_shares = _v(prior, "shares_outstanding")

        results.append(
            piotroski_f_score(
                net_income=net_income,
                operating_cash_flow=op_cf,
                roa_current=_safe_div_inline(net_income, total_assets),
                roa_prior=_safe_div_inline(prior_net_income, prior_total_assets),
                long_term_debt_current=long_term_debt_val,
                long_term_debt_prior=prior_long_term_debt,
                current_ratio_current=_safe_div_inline(current_assets, current_liabilities),
                current_ratio_prior=_safe_div_inline(prior_current_assets, prior_current_liabilities),
                shares_current=shares,
                shares_prior=prior_shares,
                gross_margin_current=_safe_div_inline(gross_profit_val, revenue),
                gross_margin_prior=_safe_div_inline(prior_gross_profit, prior_revenue),
                asset_turnover_current=_safe_div_inline(revenue, total_assets),
                asset_turnover_prior=_safe_div_inline(prior_revenue, prior_total_assets),
            )
        )

    return results


# ── 4. Store results ──────────────────────────────────────────────────────

def store_ratios(
    conn: psycopg.Connection,
    company_id: int,
    period_end: date,
    results: list[FormulaResult],
) -> int:
    """Upsert every :class:`FormulaResult` into *financial_ratios*.

    Returns the number of rows written.
    """
    sql = """
        INSERT INTO financial_ratios
            (company_id, period_end, name, value, inputs, formula_version,
             confidence, missing_penalty, computed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (company_id, period_end, name)
        DO UPDATE SET
            value           = EXCLUDED.value,
            inputs          = EXCLUDED.inputs,
            formula_version = EXCLUDED.formula_version,
            confidence      = EXCLUDED.confidence,
            missing_penalty = EXCLUDED.missing_penalty,
            computed_at     = now()
    """
    count = 0
    for r in results:
        missing_penalty = 1.0 - r.confidence if r.missing_flags else 0.0
        conn.execute(
            sql,
            (
                company_id,
                period_end,
                r.name,
                r.value,
                Jsonb(r.inputs),
                r.formula_version,
                r.confidence,
                missing_penalty,
            ),
        )
        count += 1

    return count


# ── 5. Period discovery ───────────────────────────────────────────────────

def get_annual_periods(
    conn: psycopg.Connection,
    company_id: int,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Distinct annual (10-K / FY) periods for a company, newest first."""
    rows = conn.execute(
        """
        SELECT DISTINCT fiscal_year, period_end, fiscal_period
          FROM financial_facts
         WHERE company_id    = %s
           AND fiscal_period = 'FY'
           AND form          = '10-K'
         ORDER BY period_end DESC
         LIMIT %s
        """,
        (company_id, limit),
    ).fetchall()

    return [
        {
            "fiscal_year": row[0],
            "period_end": row[1],
            "fiscal_period": row[2],
        }
        for row in rows
    ]


# ── 6. Missing-data report ───────────────────────────────────────────────

def generate_missing_data_report(
    results: list[FormulaResult],
) -> dict[str, list[str]]:
    """Return ``{formula_name: [missing_flag, …]}`` for formulas with gaps."""
    return {
        r.name: list(r.missing_flags)
        for r in results
        if r.missing_flags
    }


# ── 7. Main entry point ──────────────────────────────────────────────────

def run_for_company(
    conn: psycopg.Connection,
    company_id: int,
) -> dict[str, Any]:
    """Compute and store all fundamental + forensic ratios for every annual period.

    Returns a summary dict suitable for logging / API response.
    """
    periods = get_annual_periods(conn, company_id)
    if not periods:
        log.warning("No annual periods found for company_id=%s", company_id)
        return {
            "periods_computed": 0,
            "ratios_stored": 0,
            "missing_report": {},
            "formulas": [],
        }

    total_stored = 0
    all_results: list[FormulaResult] = []
    formula_names: set[str] = set()

    for idx, period in enumerate(periods):
        pe = period["period_end"]
        fy = period["fiscal_year"]
        fp = period["fiscal_period"]

        # The *prior* period is the next element (list is DESC by date).
        prior_pe: date | None = None
        if idx + 1 < len(periods):
            prior_pe = periods[idx + 1]["period_end"]

        log.info(
            "Computing ratios for company_id=%s  period_end=%s  fiscal_year=%s",
            company_id, pe, fy,
        )

        results = compute_all_ratios(
            conn, company_id, pe,
            prior_period_end=prior_pe,
            fiscal_year=fy,
            fiscal_period=fp,
        )
        stored = store_ratios(conn, company_id, pe, results)

        total_stored += stored
        all_results.extend(results)
        formula_names.update(r.name for r in results)

    missing_report = generate_missing_data_report(all_results)

    return {
        "periods_computed": len(periods),
        "ratios_stored": total_stored,
        "missing_report": missing_report,
        "formulas": sorted(formula_names),
    }
