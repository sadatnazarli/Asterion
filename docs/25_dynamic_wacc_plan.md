# M9 — Dynamic WACC: Research & Implementation Plan

> **M11 UPDATE (2026-06-04): Phase A IMPLEMENTED.** `app/valuation/wacc.py`
> computes a deterministic per-ticker WACC (CAPM cost of equity with
> sector/theme beta fallback; cost of debt = interest/total-debt, tax =
> income-tax/pretax, both from SEC facts with documented fallbacks). The
> reverse-DCF (`app/scoring/real_inputs.py`) discounts at this WACC instead of
> the flat 10% (fallback 10% kept only when WACC cannot be formed). Phase A uses
> static risk-free 4.5% / ERP 5.0% — **no FRED/FMP yet**. Live WACC range across
> the 9-name book: 8.89% (V) → 11.49% (NVDA). Assumptions + confidence stored per
> scorecard and summarised in `reports/wacc_summary.{md,json}`.
>
> **M12 UPDATE (2026-06-05): Phase B IMPLEMENTED.** `app/market/fred_provider.py`
> sources the risk-free rate from FRED `DGS10` (12h disk cache, falls back to
> static 4.5% with a `fallback` source flag when `FRED_API_KEY` is absent);
> `app/market/beta_provider.py` sources levered beta from FMP company profiles
> (24h cache, falls back to the Phase-A sector beta when `FMP_API_KEY` is absent,
> source recorded as `provider_beta:fmp` / `sector_fallback:<theme>` / `default`).
> `compute_wacc` now labels the method `capm_phase_b` when either live input is
> used. ERP stays a documented 5.0% assumption; cost of debt and tax remain from
> SEC facts. Added own-history valuation percentiles
> (`app/valuation/percentiles.py`): trailing P/E, EV/Revenue, P/FCF ranked vs the
> ticker's own 3–6Y history (missing history is flagged, never faked). Reports:
> `reports/macro_inputs.{md,json}`, `reports/beta_sources.{md,json}`,
> `reports/wacc_phase_b_summary.{md,json}`. API keys are never logged or returned
> (masked-suffix only via `/api/system/providers`).

**Status: DESIGN ONLY. Not implemented.** Per the M9 brief: design first,
implement only if the required FRED/FMP data actually exists. Today the
reverse-DCF (`app/quant/reverse_dcf.py`) uses a **fixed `discount_rate=0.10`**.
Every implied-growth and expectations-gap number inherits that single assumption.
A per-company, deterministic WACC removes the biggest hidden constant in the
valuation stack.

## Goal

Replace the hardcoded 10% with a deterministic `compute_wacc(ticker) → (wacc,
confidence, components, missing)` that is reproducible from public inputs, with
explicit sector fallbacks and honest confidence degradation when data is missing.
**No invented numbers** — if an input is missing, fall back to a documented
sector assumption and lower confidence; never silently fabricate a precise WACC.

## Formula (textbook, deterministic)

```
WACC = (E/V)·Re + (D/V)·Rd·(1 − Tc)

Re (cost of equity, CAPM) = Rf + β·ERP
Rd (cost of debt)         = interest_expense / total_debt   (or sector fallback)
E = market cap of equity
D = total debt (book)
V = E + D
Tc = effective tax rate = income_tax_expense / pre_tax_income (clamped 0–0.35)
```

## Input sourcing

| Input | Primary source | Have it? | Fallback |
|---|---|---|---|
| Rf (risk-free, 10Y Treasury) | **FRED** series `DGS10` | NO — no FRED client yet | static 4.25% constant w/ low confidence |
| ERP (equity risk premium) | assumption (Damodaran-style) | n/a | **fixed 5.0%** assumption (documented, not derived) |
| β (beta) | FMP / market provider | NO — finnhub/yfinance give quotes, not beta | sector-median β table |
| E (market cap) | shares × live price (finnhub) | PARTIAL — price live, shares from XBRL | book equity proxy (low confidence) |
| D (total debt) | XBRL `LongTermDebt…` | YES | 0 (flag) |
| Rd (cost of debt) | XBRL interest_expense / debt | PARTIAL — interest_expense not in concept chains yet | Rf + sector credit spread |
| Tc (tax rate) | XBRL income_tax / pre_tax | PARTIAL — concepts not yet fetched | statutory 21% |

**Verdict on availability:** of seven inputs, only total debt and (partial) market
cap are reliably present today. **Rf needs a FRED client; β needs a provider that
exposes it (FMP).** Therefore: do NOT implement the full CAPM WACC now.

## Phased implementation (only as data lands)

**Phase A — Sector-fallback WACC (implementable now, low fidelity).**
Deterministic table of sector WACC assumptions keyed off `asset_type`/sector.
Returns `(wacc, confidence≈0.4, components={"method":"sector_fallback"})`. This
already beats a single global 10% because it varies by sector. Wire it behind a
feature flag; reverse_dcf accepts an optional `discount_rate` override (it already
does) so no signature change is needed.

**Phase B — Add FRED risk-free.** Add a tiny cached FRED client
(`app/market/fred_provider.py`) for `DGS10`. Compute `Re = Rf + β_sector·ERP`
with sector β. Confidence ≈ 0.6.

**Phase C — Add beta + cost of debt.** Requires an FMP key (beta endpoint) and
extending `_CONCEPT_CHAINS` with `InterestExpense`, `IncomeTaxExpenseBenefit`,
`IncomeLossFromContinuingOperationsBeforeIncomeTaxes`. Full CAPM WACC,
confidence up to 0.9.

## Proposed module shape (not built)

```python
# app/quant/wacc.py  (DESIGN)
@dataclass(frozen=True)
class WaccResult:
    wacc: float | None
    confidence: float
    method: Literal["capm", "sector_fallback", "global_default"]
    components: dict[str, float | None]   # rf, erp, beta, re, rd, tax, e_weight, d_weight
    missing: list[str]

def compute_wacc(*, sector, market_cap, total_debt, interest_expense,
                 tax_rate, beta, risk_free, erp=0.05) -> WaccResult: ...
```

Bounds & guards: clamp WACC to **[0.05, 0.20]**; require `wacc > terminal_growth`
(reverse-DCF already rejects otherwise); tax rate clamped [0, 0.35]; if E and D
both missing → `global_default` 10% with confidence 0.2 and a loud flag.

## Decision

**Implement Phase A (sector fallback) next milestone; defer B/C until a FRED
client and an FMP/beta source exist.** Until then the reverse-DCF keeps its
explicit 10% default, now *documented as a known fixed assumption* in docs/24.
No code shipped in M9 for WACC — this is the design of record.
