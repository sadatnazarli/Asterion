"""Deterministic valuation formulas — pure functions, no DB, no LLM.

These formulas compute valuation-related metrics from SEC financial data.
No market price data required for this initial version (M2 scope).

Note: Market-cap-dependent ratios (PE, PB, EV multiples) require price data
that may not be available from SEC alone. These return None with appropriate
missing_flags when market_cap is not provided.
"""
from __future__ import annotations

from app.quant.fundamentals import FormulaResult, _safe_div, _to_float

FORMULA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Valuation formulas
# ---------------------------------------------------------------------------


def enterprise_value(
    market_cap: float | None,
    total_debt: float | None,
    cash_and_equivalents: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute Enterprise Value = market_cap + total_debt - cash_and_equivalents.

    Parameters
    ----------
    market_cap:
        Total market capitalisation (shares outstanding × price).
    total_debt:
        Total short-term + long-term debt.
    cash_and_equivalents:
        Cash and cash-equivalents on the balance sheet.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    mc = _to_float(market_cap)
    debt = _to_float(total_debt)
    cash = _to_float(cash_and_equivalents)

    if mc is None:
        missing.append("market_cap")
    if debt is None:
        missing.append("total_debt")
    if cash is None:
        missing.append("cash_and_equivalents")

    inputs: dict[str, object] = {
        "market_cap": mc,
        "total_debt": debt,
        "cash_and_equivalents": cash,
    }

    # market_cap is essential — without it EV is meaningless
    if mc is None:
        return FormulaResult(
            name="enterprise_value",
            value=None,
            inputs=inputs,
            formula_version=FORMULA_VERSION,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=source_fact_ids or [],
        )

    # Treat missing debt / cash as zero (common conservative assumption)
    debt = debt if debt is not None else 0.0
    cash = cash if cash is not None else 0.0

    value = mc + debt - cash
    confidence = 1.0 - 0.1 * len(missing)

    return FormulaResult(
        name="enterprise_value",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def ev_to_revenue(
    enterprise_value_val: float | None,
    revenue: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute EV / Revenue.

    Parameters
    ----------
    enterprise_value_val:
        Pre-computed enterprise value.
    revenue:
        Total revenue for the period.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    ev = _to_float(enterprise_value_val)
    rev = _to_float(revenue)

    if ev is None:
        missing.append("enterprise_value")
    if rev is None:
        missing.append("revenue")

    inputs: dict[str, object] = {
        "enterprise_value": ev,
        "revenue": rev,
    }

    value = _safe_div(ev, rev)
    if value is None and "enterprise_value" not in missing and "revenue" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="ev_to_revenue",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def ev_to_ebitda(
    enterprise_value_val: float | None,
    ebitda: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute EV / EBITDA.

    Parameters
    ----------
    enterprise_value_val:
        Pre-computed enterprise value.
    ebitda:
        Earnings before interest, taxes, depreciation, and amortisation.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    ev = _to_float(enterprise_value_val)
    eb = _to_float(ebitda)

    if ev is None:
        missing.append("enterprise_value")
    if eb is None:
        missing.append("ebitda")

    inputs: dict[str, object] = {
        "enterprise_value": ev,
        "ebitda": eb,
    }

    value = _safe_div(ev, eb)
    if value is None and "enterprise_value" not in missing and "ebitda" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="ev_to_ebitda",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def price_to_earnings(
    market_cap: float | None,
    net_income: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute Price-to-Earnings ratio = market_cap / net_income.

    Parameters
    ----------
    market_cap:
        Total market capitalisation.
    net_income:
        Net income for the period.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    mc = _to_float(market_cap)
    ni = _to_float(net_income)

    if mc is None:
        missing.append("market_cap")
    if ni is None:
        missing.append("net_income")

    inputs: dict[str, object] = {
        "market_cap": mc,
        "net_income": ni,
    }

    value = _safe_div(mc, ni)
    if value is None and "market_cap" not in missing and "net_income" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="pe_ratio",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def price_to_book(
    market_cap: float | None,
    book_value: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute Price-to-Book ratio = market_cap / book_value.

    Parameters
    ----------
    market_cap:
        Total market capitalisation.
    book_value:
        Total shareholders' equity (book value).
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    mc = _to_float(market_cap)
    bv = _to_float(book_value)

    if mc is None:
        missing.append("market_cap")
    if bv is None:
        missing.append("book_value")

    inputs: dict[str, object] = {
        "market_cap": mc,
        "book_value": bv,
    }

    value = _safe_div(mc, bv)
    if value is None and "market_cap" not in missing and "book_value" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="pb_ratio",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def price_to_fcf(
    market_cap: float | None,
    free_cash_flow: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute Price-to-Free-Cash-Flow = market_cap / free_cash_flow.

    Parameters
    ----------
    market_cap:
        Total market capitalisation.
    free_cash_flow:
        Free cash flow for the period.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    mc = _to_float(market_cap)
    fcf = _to_float(free_cash_flow)

    if mc is None:
        missing.append("market_cap")
    if fcf is None:
        missing.append("free_cash_flow")

    inputs: dict[str, object] = {
        "market_cap": mc,
        "free_cash_flow": fcf,
    }

    value = _safe_div(mc, fcf)
    if value is None and "market_cap" not in missing and "free_cash_flow" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="p_to_fcf",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def fcf_yield(
    free_cash_flow: float | None,
    market_cap: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute FCF Yield = free_cash_flow / market_cap.

    Parameters
    ----------
    free_cash_flow:
        Free cash flow for the period.
    market_cap:
        Total market capitalisation.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    fcf = _to_float(free_cash_flow)
    mc = _to_float(market_cap)

    if fcf is None:
        missing.append("free_cash_flow")
    if mc is None:
        missing.append("market_cap")

    inputs: dict[str, object] = {
        "free_cash_flow": fcf,
        "market_cap": mc,
    }

    value = _safe_div(fcf, mc)
    if value is None and "free_cash_flow" not in missing and "market_cap" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="fcf_yield",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )


def earnings_yield(
    net_income: float | None,
    enterprise_value_val: float | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Compute Earnings Yield = net_income / enterprise_value.

    Parameters
    ----------
    net_income:
        Net income for the period.
    enterprise_value_val:
        Pre-computed enterprise value.
    source_fact_ids:
        Optional list of ``financial_facts.id`` values that contributed.

    Returns
    -------
    FormulaResult
    """
    missing: list[str] = []
    ni = _to_float(net_income)
    ev = _to_float(enterprise_value_val)

    if ni is None:
        missing.append("net_income")
    if ev is None:
        missing.append("enterprise_value")

    inputs: dict[str, object] = {
        "net_income": ni,
        "enterprise_value": ev,
    }

    value = _safe_div(ni, ev)
    if value is None and "net_income" not in missing and "enterprise_value" not in missing:
        missing.append("division_by_zero")

    confidence = 1.0 - 0.2 * len(missing) if value is not None else 0.0

    return FormulaResult(
        name="earnings_yield",
        value=value,
        inputs=inputs,
        formula_version=FORMULA_VERSION,
        confidence=max(confidence, 0.0),
        missing_flags=missing,
        source_fact_ids=source_fact_ids or [],
    )
