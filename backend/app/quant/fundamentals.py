"""Deterministic fundamental ratio formulas — pure functions, no DB, no LLM.

Every function takes numeric inputs and returns a FormulaResult dataclass.
Formula version is bumped on any logic change. All results carry provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


FORMULA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class FormulaResult:
    """Standardised output of every quant formula."""

    name: str
    value: float | None
    inputs: dict[str, Any]  # raw numbers fed in (reproducibility)
    formula_version: str = FORMULA_VERSION
    confidence: float = 1.0  # 0..1; lowered when inputs are imputed
    missing_flags: list[str] = field(default_factory=list)
    source_fact_ids: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_float(v: Any) -> float | None:
    """Coerce Decimal/int/str to float, None stays None."""
    if v is None:
        return None
    if isinstance(v, float):
        return v
    if isinstance(v, (int, Decimal)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division returning None on zero/None denominator."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0.0:
        return None
    return numerator / denominator


def _check_missing(
    params: dict[str, Any],
) -> tuple[dict[str, float | None], list[str]]:
    """Convert all params to float and return (converted_dict, missing_flags).

    Each key whose value resolves to ``None`` is added to *missing_flags*.
    """
    converted: dict[str, float | None] = {}
    missing: list[str] = []
    for name, raw in params.items():
        val = _to_float(raw)
        converted[name] = val
        if val is None:
            missing.append(name)
    return converted, missing


def _ids(source_fact_ids: list[int] | None) -> list[int]:
    """Normalise optional fact-id list."""
    return list(source_fact_ids) if source_fact_ids else []


# ---------------------------------------------------------------------------
# Formula functions
# ---------------------------------------------------------------------------


def revenue_growth(
    current_revenue: float | Decimal | None,
    prior_revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Year-over-year revenue growth rate.

    Formula: ``(current - prior) / abs(prior)``
    """
    raw_inputs: dict[str, Any] = {
        "current_revenue": current_revenue,
        "prior_revenue": prior_revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="revenue_growth",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    cur = vals["current_revenue"]
    prior = vals["prior_revenue"]
    assert cur is not None and prior is not None  # guaranteed by _check_missing

    if prior == 0.0:
        return FormulaResult(
            name="revenue_growth",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = (cur - prior) / abs(prior)
    return FormulaResult(
        name="revenue_growth",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def gross_margin(
    gross_profit: float | Decimal | None,
    revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Gross margin ratio.

    Formula: ``gross_profit / revenue``
    """
    raw_inputs: dict[str, Any] = {
        "gross_profit": gross_profit,
        "revenue": revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="gross_margin",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["revenue"]
    if denom == 0.0:
        return FormulaResult(
            name="gross_margin",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["gross_profit"], denom)
    return FormulaResult(
        name="gross_margin",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def operating_margin(
    operating_income: float | Decimal | None,
    revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Operating margin ratio.

    Formula: ``operating_income / revenue``
    """
    raw_inputs: dict[str, Any] = {
        "operating_income": operating_income,
        "revenue": revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="operating_margin",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["revenue"]
    if denom == 0.0:
        return FormulaResult(
            name="operating_margin",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["operating_income"], denom)
    return FormulaResult(
        name="operating_margin",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def net_margin(
    net_income: float | Decimal | None,
    revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Net profit margin.

    Formula: ``net_income / revenue``
    """
    raw_inputs: dict[str, Any] = {
        "net_income": net_income,
        "revenue": revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="net_margin",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["revenue"]
    if denom == 0.0:
        return FormulaResult(
            name="net_margin",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["net_income"], denom)
    return FormulaResult(
        name="net_margin",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def free_cash_flow_margin(
    operating_cash_flow: float | Decimal | None,
    capex: float | Decimal | None,
    revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Free-cash-flow margin.

    Formula: ``(operating_cash_flow - abs(capex)) / revenue``

    *capex* is typically reported as a negative number in SEC filings,
    so ``abs()`` is applied to normalise it before subtraction.
    """
    raw_inputs: dict[str, Any] = {
        "operating_cash_flow": operating_cash_flow,
        "capex": capex,
        "revenue": revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="fcf_margin",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["revenue"]
    if denom == 0.0:
        return FormulaResult(
            name="fcf_margin",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    ocf = vals["operating_cash_flow"]
    cx = vals["capex"]
    assert ocf is not None and cx is not None  # guaranteed by _check_missing

    fcf = ocf - abs(cx)
    value = fcf / denom  # type: ignore[operator]
    return FormulaResult(
        name="fcf_margin",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def return_on_equity(
    net_income: float | Decimal | None,
    shareholders_equity: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Return on equity.

    Formula: ``net_income / shareholders_equity``
    """
    raw_inputs: dict[str, Any] = {
        "net_income": net_income,
        "shareholders_equity": shareholders_equity,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="roe",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["shareholders_equity"]
    if denom == 0.0:
        return FormulaResult(
            name="roe",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["net_income"], denom)
    return FormulaResult(
        name="roe",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def return_on_assets(
    net_income: float | Decimal | None,
    total_assets: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Return on assets.

    Formula: ``net_income / total_assets``
    """
    raw_inputs: dict[str, Any] = {
        "net_income": net_income,
        "total_assets": total_assets,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="roa",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["total_assets"]
    if denom == 0.0:
        return FormulaResult(
            name="roa",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["net_income"], denom)
    return FormulaResult(
        name="roa",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def current_ratio(
    current_assets: float | Decimal | None,
    current_liabilities: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Current ratio (liquidity).

    Formula: ``current_assets / current_liabilities``
    """
    raw_inputs: dict[str, Any] = {
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="current_ratio",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["current_liabilities"]
    if denom == 0.0:
        return FormulaResult(
            name="current_ratio",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["current_assets"], denom)
    return FormulaResult(
        name="current_ratio",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def debt_to_equity(
    total_debt: float | Decimal | None,
    shareholders_equity: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Debt-to-equity ratio.

    Formula: ``total_debt / shareholders_equity``
    """
    raw_inputs: dict[str, Any] = {
        "total_debt": total_debt,
        "shareholders_equity": shareholders_equity,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="debt_to_equity",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["shareholders_equity"]
    if denom == 0.0:
        return FormulaResult(
            name="debt_to_equity",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["total_debt"], denom)
    return FormulaResult(
        name="debt_to_equity",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def sbc_to_revenue(
    sbc: float | Decimal | None,
    revenue: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Stock-based compensation as a fraction of revenue.

    Formula: ``sbc / revenue``
    """
    raw_inputs: dict[str, Any] = {
        "sbc": sbc,
        "revenue": revenue,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="sbc_to_revenue",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["revenue"]
    if denom == 0.0:
        return FormulaResult(
            name="sbc_to_revenue",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["sbc"], denom)
    return FormulaResult(
        name="sbc_to_revenue",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def sbc_to_operating_cash_flow(
    sbc: float | Decimal | None,
    operating_cash_flow: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Stock-based compensation as a fraction of operating cash flow.

    Formula: ``sbc / operating_cash_flow``
    """
    raw_inputs: dict[str, Any] = {
        "sbc": sbc,
        "operating_cash_flow": operating_cash_flow,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="sbc_to_ocf",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    denom = vals["operating_cash_flow"]
    if denom == 0.0:
        return FormulaResult(
            name="sbc_to_ocf",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = _safe_div(vals["sbc"], denom)
    return FormulaResult(
        name="sbc_to_ocf",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )


def shares_outstanding_change(
    current_shares: float | Decimal | None,
    prior_shares: float | Decimal | None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Period-over-period change in shares outstanding.

    Formula: ``(current - prior) / prior``
    """
    raw_inputs: dict[str, Any] = {
        "current_shares": current_shares,
        "prior_shares": prior_shares,
    }
    vals, missing = _check_missing(raw_inputs)

    if missing:
        return FormulaResult(
            name="shares_outstanding_change",
            value=None,
            inputs=raw_inputs,
            confidence=0.0,
            missing_flags=missing,
            source_fact_ids=_ids(source_fact_ids),
        )

    cur = vals["current_shares"]
    prior = vals["prior_shares"]
    assert cur is not None and prior is not None  # guaranteed by _check_missing

    if prior == 0.0:
        return FormulaResult(
            name="shares_outstanding_change",
            value=None,
            inputs=raw_inputs,
            confidence=1.0,
            missing_flags=["zero_denominator"],
            source_fact_ids=_ids(source_fact_ids),
        )

    value = (cur - prior) / prior
    return FormulaResult(
        name="shares_outstanding_change",
        value=value,
        inputs=raw_inputs,
        source_fact_ids=_ids(source_fact_ids),
    )
