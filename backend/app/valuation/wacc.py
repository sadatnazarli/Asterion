"""Dynamic WACC — Phase A (deterministic, no FRED/FMP).

Replaces the fixed 10% discount rate used by the reverse-DCF. Phase A is fully
self-contained: it uses sensible static defaults for the risk-free rate and
equity-risk premium, a sector/theme beta lookup, and pulls cost-of-debt and the
effective tax rate from SEC facts when available — otherwise it falls back and
records the fallback in ``missing_flags`` (confidence degrades, never faked).

WACC = w_e · Ke + w_d · Kd · (1 − tax)
  Ke (CAPM) = risk_free + beta · ERP
  Kd        = interest_expense / total_debt   (else fallback)
  tax       = income_tax / pretax_income      (else fallback)

Phase B (not here) will source risk_free from FRED and beta from market data;
see docs/25_dynamic_wacc_plan.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import psycopg

from app.quant.scoring_inputs import (
    get_fact_value,
    get_fact_value_for_period,
    _CONCEPT_CHAINS,
)

# ── Phase-A deterministic defaults ─────────────────────────────────────────
DEFAULT_RISK_FREE_RATE = 0.045      # ~10Y UST, static until FRED (Phase B)
DEFAULT_EQUITY_RISK_PREMIUM = 0.050  # long-run US equity premium
DEFAULT_COST_OF_DEBT = 0.050         # used when interest/debt unavailable
DEFAULT_TAX_RATE = 0.21              # US federal statutory
FALLBACK_WACC = 0.10                 # last resort if WACC cannot be computed

# Cost-of-debt sanity band — outside this, treat the facts as unreliable.
_KD_MIN, _KD_MAX = 0.01, 0.15
# Effective-tax sanity band.
_TAX_MIN, _TAX_MAX = 0.0, 0.50

# ── Sector / theme beta fallbacks (Phase A) ────────────────────────────────
# No live beta source yet, so bucket by theme. Values are conventional levered
# beta estimates; override per Phase B once a market beta feed exists.
THEME_BETA: dict[str, float] = {
    "mega_cap_tech": 1.05,
    "semiconductor": 1.40,
    "fintech": 1.05,
    "biotech_speculative": 1.20,
    "speculative_tech": 1.30,
    "industrial_tech": 1.15,
    "etf": 1.00,
    "default": 1.10,
}

# Universe → theme. Anything unmapped uses "default" (beta 1.10).
SYMBOL_THEME: dict[str, str] = {
    # mega-cap tech / platforms
    "META": "mega_cap_tech", "MSFT": "mega_cap_tech", "GOOGL": "mega_cap_tech",
    "AMZN": "mega_cap_tech",
    # semiconductors / hardware
    "NVDA": "semiconductor", "MU": "semiconductor", "ASML": "semiconductor",
    "TSM": "semiconductor", "AMD": "semiconductor",
    # fintech / financials
    "V": "fintech", "BLK": "fintech", "NU": "fintech", "MELI": "fintech",
    # biotech / pharma
    "ACRS": "biotech_speculative", "LLY": "biotech_speculative",
    "NVO": "biotech_speculative",
    # speculative / high-beta growth
    "PLTR": "speculative_tech", "CRWD": "speculative_tech",
    "NET": "speculative_tech", "SHOP": "speculative_tech", "RKLB": "speculative_tech",
    # industrial / power infra
    "VRT": "industrial_tech",
}

DEFAULT_BETA = THEME_BETA["default"]


def beta_for_symbol(symbol: str) -> tuple[float, str]:
    """Return ``(beta, source)`` for *symbol* from the static theme map."""
    theme = SYMBOL_THEME.get(symbol.upper())
    if theme is None:
        return DEFAULT_BETA, "default"
    return THEME_BETA[theme], f"sector_fallback:{theme}"


@dataclass
class WaccResult:
    wacc: float
    method: str                       # "capm_phase_a" or "fallback"
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    beta_source: str
    cost_of_equity: float
    cost_of_debt: float
    cost_of_debt_source: str          # "interest_expense/total_debt" | "fallback"
    tax_rate: float
    tax_rate_source: str              # "income_tax/pretax" | "fallback"
    weight_equity: float
    weight_debt: float
    confidence: float
    missing_flags: list[str] = field(default_factory=list)
    risk_free_source: str = "static_default"   # "fred:DGS10" | "fred_cache:DGS10" | "fallback" | "static_default"

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["missing_flags"] = list(self.missing_flags)
        return d


def compute_wacc(
    *,
    market_cap: float | None,
    total_debt: float | None,
    beta: float,
    beta_source: str,
    interest_expense: float | None = None,
    income_tax: float | None = None,
    pretax_income: float | None = None,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    equity_risk_premium: float = DEFAULT_EQUITY_RISK_PREMIUM,
    risk_free_source: str = "static_default",
) -> WaccResult | None:
    """Compute CAPM WACC from primitives. Pure (no DB / network).

    Phase A passes the static risk-free / sector beta; Phase B (M12) passes a
    FRED-sourced ``risk_free_rate`` and/or an FMP ``beta`` with the matching
    ``beta_source`` / ``risk_free_source``. The method label reflects whichever
    inputs were live.

    Returns ``None`` only when WACC genuinely cannot be formed (no market cap to
    weight equity) — the caller then keeps the 10% fallback.
    """
    missing: list[str] = []
    confidence = 1.0

    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    if beta_source == "default":
        confidence -= 0.15  # generic beta, not theme-specific

    # cost of debt
    if (
        interest_expense is not None
        and total_debt not in (None, 0)
        and total_debt > 0
    ):
        kd = abs(interest_expense) / total_debt
        if _KD_MIN <= kd <= _KD_MAX:
            cost_of_debt = kd
            cost_of_debt_source = "interest_expense/total_debt"
        else:
            cost_of_debt = DEFAULT_COST_OF_DEBT
            cost_of_debt_source = "fallback"
            missing.append("cost_of_debt_out_of_band")
            confidence -= 0.10
    else:
        cost_of_debt = DEFAULT_COST_OF_DEBT
        cost_of_debt_source = "fallback"
        missing.append("cost_of_debt")
        confidence -= 0.10

    # effective tax rate
    if pretax_income is not None and pretax_income > 0 and income_tax is not None:
        eff = income_tax / pretax_income
        if _TAX_MIN <= eff <= _TAX_MAX:
            tax_rate = eff
            tax_rate_source = "income_tax/pretax"
        else:
            tax_rate = DEFAULT_TAX_RATE
            tax_rate_source = "fallback"
            missing.append("tax_rate_out_of_band")
            confidence -= 0.05
    else:
        tax_rate = DEFAULT_TAX_RATE
        tax_rate_source = "fallback"
        missing.append("tax_rate")
        confidence -= 0.05

    # capital-structure weights
    if market_cap is None or market_cap <= 0:
        # cannot weight equity → caller keeps 10% fallback
        return None
    debt = total_debt if (total_debt is not None and total_debt > 0) else 0.0
    if debt == 0.0:
        missing.append("total_debt")
        confidence -= 0.05
    total_cap = market_cap + debt
    w_e = market_cap / total_cap
    w_d = debt / total_cap

    wacc = w_e * cost_of_equity + w_d * cost_of_debt * (1.0 - tax_rate)
    confidence = max(0.0, min(1.0, confidence))

    # Live inputs (FRED rate or provider beta) ⇒ Phase B; else Phase A.
    phase_b = risk_free_source.startswith("fred") or beta_source.startswith("provider_beta")
    method = "capm_phase_b" if phase_b else "capm_phase_a"

    return WaccResult(
        wacc=wacc,
        method=method,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        beta=beta,
        beta_source=beta_source,
        cost_of_equity=cost_of_equity,
        cost_of_debt=cost_of_debt,
        cost_of_debt_source=cost_of_debt_source,
        tax_rate=tax_rate,
        tax_rate_source=tax_rate_source,
        weight_equity=w_e,
        weight_debt=w_d,
        confidence=confidence,
        missing_flags=missing,
        risk_free_source=risk_free_source,
    )


def wacc_for_company(
    conn: psycopg.Connection,
    company_id: int,
    symbol: str,
    *,
    market_cap: float | None,
    total_debt: float | None,
    period_end,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    use_providers: bool = True,
) -> WaccResult | None:
    """Pull interest/tax/pretax from facts for this period and compute WACC.

    Uses fiscal_year/period matching first (consistent with how the line items
    are fetched), then a date-window fallback. When *use_providers* (M12 Phase B),
    the risk-free rate comes from FRED and beta from FMP if those keys exist —
    both degrade cleanly to the static / sector fallbacks otherwise.
    """
    # Phase B: live risk-free (FRED) + live beta (FMP), each with honest fallback.
    # Imported lazily to avoid an import cycle (beta_provider imports this module).
    risk_free_rate = DEFAULT_RISK_FREE_RATE
    risk_free_source = "static_default"
    if use_providers:
        from app.market.beta_provider import get_beta
        from app.market.fred_provider import get_risk_free_rate

        macro = get_risk_free_rate()
        risk_free_rate = macro.risk_free_rate
        risk_free_source = macro.source
        br = get_beta(symbol)
        beta, beta_source = br.beta, br.source
    else:
        beta, beta_source = beta_for_symbol(symbol)

    def _fetch(chain: str) -> float | None:
        if fiscal_year is not None and fiscal_period is not None:
            v, _ = get_fact_value_for_period(
                conn, company_id, _CONCEPT_CHAINS[chain], fiscal_year, fiscal_period,
            )
            if v is not None:
                return v
        v, _ = get_fact_value(
            conn, company_id, _CONCEPT_CHAINS[chain], period_end,
            fiscal_period=fiscal_period,
        )
        return v

    ie = _fetch("interest_expense")
    tax = _fetch("income_tax_expense")
    pretax = _fetch("pretax_income")

    return compute_wacc(
        market_cap=market_cap,
        total_debt=total_debt,
        beta=beta,
        beta_source=beta_source,
        interest_expense=ie,
        income_tax=tax,
        pretax_income=pretax,
        risk_free_rate=risk_free_rate,
        risk_free_source=risk_free_source,
    )
