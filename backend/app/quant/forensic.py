"""Forensic accounting formulas — Altman Z-score, Piotroski F-score, accruals.

Pure deterministic functions. No DB, no LLM. These identify red flags and
quality signals from SEC financial data.
"""

from __future__ import annotations

from app.quant.fundamentals import FormulaResult, _safe_div, _to_float

FORMULA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------

def altman_z_score(
    working_capital: float | None = None,
    retained_earnings: float | None = None,
    ebit: float | None = None,
    market_cap: float | None = None,
    total_liabilities: float | None = None,
    revenue: float | None = None,
    total_assets: float | None = None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Original Altman Z-Score for bankruptcy prediction.

    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Where:
        X1 = Working Capital / Total Assets
        X2 = Retained Earnings / Total Assets
        X3 = EBIT / Total Assets
        X4 = Market Value of Equity / Total Liabilities
        X5 = Revenue / Total Assets

    Returns *None* value when total_assets is missing/zero or market_cap is
    missing (private-firm variant not supported without book equity).
    """
    ta = _to_float(total_assets)
    inputs_used: dict[str, float | None] = {
        "working_capital": _to_float(working_capital),
        "retained_earnings": _to_float(retained_earnings),
        "ebit": _to_float(ebit),
        "market_cap": _to_float(market_cap),
        "total_liabilities": _to_float(total_liabilities),
        "revenue": _to_float(revenue),
        "total_assets": ta,
    }
    missing_flags: list[str] = []

    # Hard requirement: total_assets must be present and non-zero.
    if ta is None or ta == 0.0:
        missing_flags.append("total_assets")
        return FormulaResult(
            name="altman_z_score",
            value=None,
            inputs=inputs_used,
            formula_version=FORMULA_VERSION,
            confidence=0.0,
            missing_flags=missing_flags,
            source_fact_ids=source_fact_ids or [],
        )

    # Hard requirement: market_cap must be present (no private-firm variant).
    mc = _to_float(market_cap)
    if mc is None:
        missing_flags.append("market_cap")
        return FormulaResult(
            name="altman_z_score",
            value=None,
            inputs=inputs_used,
            formula_version=FORMULA_VERSION,
            confidence=0.0,
            missing_flags=missing_flags,
            source_fact_ids=source_fact_ids or [],
        )

    # --- Compute each component, tracking availability ----------------------
    coefficients = [1.2, 1.4, 3.3, 0.6, 1.0]
    component_names = [
        "working_capital",
        "retained_earnings",
        "ebit",
        "market_cap",  # stands for the X4 ratio
        "revenue",
    ]

    wc = _to_float(working_capital)
    re_ = _to_float(retained_earnings)
    eb = _to_float(ebit)
    tl = _to_float(total_liabilities)
    rev = _to_float(revenue)

    x_values: list[float] = []
    available_count = 0

    # X1 = Working Capital / Total Assets
    if wc is not None:
        x_values.append(wc / ta)
        available_count += 1
    else:
        x_values.append(0.0)
        missing_flags.append("working_capital")

    # X2 = Retained Earnings / Total Assets
    if re_ is not None:
        x_values.append(re_ / ta)
        available_count += 1
    else:
        x_values.append(0.0)
        missing_flags.append("retained_earnings")

    # X3 = EBIT / Total Assets
    if eb is not None:
        x_values.append(eb / ta)
        available_count += 1
    else:
        x_values.append(0.0)
        missing_flags.append("ebit")

    # X4 = Market Cap / Total Liabilities
    # market_cap already confirmed non-None above
    if tl is not None and tl != 0.0:
        x_values.append(mc / tl)
        available_count += 1
    else:
        x_values.append(0.0)
        if tl is None:
            missing_flags.append("total_liabilities")
        else:
            # tl == 0 means division impossible; treat as missing
            missing_flags.append("total_liabilities")

    # X5 = Revenue / Total Assets
    if rev is not None:
        x_values.append(rev / ta)
        available_count += 1
    else:
        x_values.append(0.0)
        missing_flags.append("revenue")

    z = sum(c * x for c, x in zip(coefficients, x_values))
    confidence = available_count / 5

    return FormulaResult(
        name="altman_z_score",
        value=round(z, 6),
        inputs=inputs_used,
        formula_version=FORMULA_VERSION,
        confidence=round(confidence, 4),
        missing_flags=missing_flags,
        source_fact_ids=source_fact_ids or [],
    )


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

def piotroski_f_score(
    *,
    # Profitability
    net_income: float | None = None,
    operating_cash_flow: float | None = None,
    roa_current: float | None = None,
    roa_prior: float | None = None,
    # Leverage / Liquidity
    long_term_debt_current: float | None = None,
    long_term_debt_prior: float | None = None,
    current_ratio_current: float | None = None,
    current_ratio_prior: float | None = None,
    shares_current: float | None = None,
    shares_prior: float | None = None,
    # Operating Efficiency
    gross_margin_current: float | None = None,
    gross_margin_prior: float | None = None,
    asset_turnover_current: float | None = None,
    asset_turnover_prior: float | None = None,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Piotroski F-Score (0-9) measuring fundamental financial strength.

    Nine binary criteria across three categories:

    **Profitability (4 pts):**
        F1 – Positive ROA (net_income > 0 as proxy if ROA unavailable)
        F2 – Positive operating cash flow
        F3 – Improving ROA (current > prior)
        F4 – Cash flow > net income (quality of earnings)

    **Leverage / Liquidity / Source of Funds (3 pts):**
        F5 – Long-term debt decreased
        F6 – Current ratio improved
        F7 – No new shares issued

    **Operating Efficiency (2 pts):**
        F8 – Gross margin improved
        F9 – Asset turnover improved

    Missing data → criterion is not scored (neither 0 nor 1).
    """
    ni = _to_float(net_income)
    ocf = _to_float(operating_cash_flow)
    roa_c = _to_float(roa_current)
    roa_p = _to_float(roa_prior)
    ltd_c = _to_float(long_term_debt_current)
    ltd_p = _to_float(long_term_debt_prior)
    cr_c = _to_float(current_ratio_current)
    cr_p = _to_float(current_ratio_prior)
    sh_c = _to_float(shares_current)
    sh_p = _to_float(shares_prior)
    gm_c = _to_float(gross_margin_current)
    gm_p = _to_float(gross_margin_prior)
    at_c = _to_float(asset_turnover_current)
    at_p = _to_float(asset_turnover_prior)

    inputs_used: dict[str, float | None] = {
        "net_income": ni,
        "operating_cash_flow": ocf,
        "roa_current": roa_c,
        "roa_prior": roa_p,
        "long_term_debt_current": ltd_c,
        "long_term_debt_prior": ltd_p,
        "current_ratio_current": cr_c,
        "current_ratio_prior": cr_p,
        "shares_current": sh_c,
        "shares_prior": sh_p,
        "gross_margin_current": gm_c,
        "gross_margin_prior": gm_p,
        "asset_turnover_current": at_c,
        "asset_turnover_prior": at_p,
    }

    score = 0
    criteria_scored = 0
    missing_flags: list[str] = []

    # --- Profitability -------------------------------------------------------

    # F1: Positive ROA (use net_income > 0 as proxy if roa_current absent)
    if roa_c is not None:
        criteria_scored += 1
        if roa_c > 0:
            score += 1
    elif ni is not None:
        criteria_scored += 1
        if ni > 0:
            score += 1
    else:
        missing_flags.append("F1")

    # F2: Operating cash flow > 0
    if ocf is not None:
        criteria_scored += 1
        if ocf > 0:
            score += 1
    else:
        missing_flags.append("F2")

    # F3: ROA improving (current > prior)
    if roa_c is not None and roa_p is not None:
        criteria_scored += 1
        if roa_c > roa_p:
            score += 1
    else:
        missing_flags.append("F3")

    # F4: OCF > Net Income (quality of earnings / accruals signal)
    if ocf is not None and ni is not None:
        criteria_scored += 1
        if ocf > ni:
            score += 1
    else:
        missing_flags.append("F4")

    # --- Leverage / Liquidity / Source of Funds ------------------------------

    # F5: Long-term debt decreased
    if ltd_c is not None and ltd_p is not None:
        criteria_scored += 1
        if ltd_c < ltd_p:
            score += 1
    else:
        missing_flags.append("F5")

    # F6: Current ratio improved
    if cr_c is not None and cr_p is not None:
        criteria_scored += 1
        if cr_c > cr_p:
            score += 1
    else:
        missing_flags.append("F6")

    # F7: No new shares issued (shares outstanding did not increase)
    if sh_c is not None and sh_p is not None:
        criteria_scored += 1
        if sh_c <= sh_p:
            score += 1
    else:
        missing_flags.append("F7")

    # --- Operating Efficiency ------------------------------------------------

    # F8: Gross margin improved
    if gm_c is not None and gm_p is not None:
        criteria_scored += 1
        if gm_c > gm_p:
            score += 1
    else:
        missing_flags.append("F8")

    # F9: Asset turnover improved
    if at_c is not None and at_p is not None:
        criteria_scored += 1
        if at_c > at_p:
            score += 1
    else:
        missing_flags.append("F9")

    confidence = criteria_scored / 9 if criteria_scored > 0 else 0.0

    return FormulaResult(
        name="piotroski_f_score",
        value=score,
        inputs=inputs_used,
        formula_version=FORMULA_VERSION,
        confidence=round(confidence, 4),
        missing_flags=missing_flags,
        source_fact_ids=source_fact_ids or [],
    )


# ---------------------------------------------------------------------------
# Accruals Ratio
# ---------------------------------------------------------------------------

def accruals_ratio(
    net_income: float | None = None,
    operating_cash_flow: float | None = None,
    total_assets: float | None = None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Balance-sheet accruals ratio.

    Formula::

        accruals_ratio = (net_income - operating_cash_flow) / total_assets

    Lower (more negative) values indicate higher earnings quality — cash
    earnings exceed accounting earnings.
    """
    ni = _to_float(net_income)
    ocf = _to_float(operating_cash_flow)
    ta = _to_float(total_assets)

    inputs_used: dict[str, float | None] = {
        "net_income": ni,
        "operating_cash_flow": ocf,
        "total_assets": ta,
    }
    missing_flags: list[str] = []

    if ni is None:
        missing_flags.append("net_income")
    if ocf is None:
        missing_flags.append("operating_cash_flow")
    if ta is None:
        missing_flags.append("total_assets")

    value = _safe_div(
        (ni - ocf) if (ni is not None and ocf is not None) else None,
        ta,
    )

    if value is not None:
        value = round(value, 6)

    confidence: float
    if value is not None:
        confidence = 1.0
    elif not missing_flags:
        # total_assets was zero
        confidence = 0.0
    else:
        confidence = 0.0

    return FormulaResult(
        name="accruals_ratio",
        value=value,
        inputs=inputs_used,
        formula_version=FORMULA_VERSION,
        confidence=confidence,
        missing_flags=missing_flags,
        source_fact_ids=source_fact_ids or [],
    )


# ---------------------------------------------------------------------------
# Quality of Earnings
# ---------------------------------------------------------------------------

def quality_of_earnings(
    operating_cash_flow: float | None = None,
    net_income: float | None = None,
    *,
    source_fact_ids: list[int] | None = None,
) -> FormulaResult:
    """Quality-of-earnings ratio.

    Formula::

        quality_of_earnings = operating_cash_flow / net_income

    Values > 1.0 indicate cash flow exceeds reported earnings — a positive
    quality signal.  Returns *None* when net_income is zero or either input
    is missing.
    """
    ocf = _to_float(operating_cash_flow)
    ni = _to_float(net_income)

    inputs_used: dict[str, float | None] = {
        "operating_cash_flow": ocf,
        "net_income": ni,
    }
    missing_flags: list[str] = []

    if ocf is None:
        missing_flags.append("operating_cash_flow")
    if ni is None:
        missing_flags.append("net_income")

    value = _safe_div(ocf, ni)

    if value is not None:
        value = round(value, 6)

    confidence: float
    if value is not None:
        confidence = 1.0
    elif not missing_flags:
        # net_income was zero
        confidence = 0.0
    else:
        confidence = 0.0

    return FormulaResult(
        name="quality_of_earnings",
        value=value,
        inputs=inputs_used,
        formula_version=FORMULA_VERSION,
        confidence=confidence,
        missing_flags=missing_flags,
        source_fact_ids=source_fact_ids or [],
    )
