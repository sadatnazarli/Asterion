# M9 — Formula Inventory & Audit

> **M10 UPDATE (2026-06-04):** the mock-input finding below has been FIXED. The
> mock `AdvancedInputsFetcher` constants are removed; advanced scores are now fed
> real per-ticker data via `app/scoring/real_inputs.py` + `scorecard_generator.py`.
> Scores now vary across tickers (see `reports/advanced_score_variance.md`:
> cross-ticker stdev went 0.0 → 13.8–35). `reflexivity_risk` is renamed *Financial
> Reflexivity / Market-Structure Risk* (MVP). Remaining gaps: capex often absent
> from SEC facts → no FCF → reverse-DCF (implied_growth / DCF-sensitivity) degrades
> to low confidence; `misunderstood_change` still lacks a sentiment feed. The
> sections below describe the pre-M10 state; calibration maturities in
> `app/scoring/calibration.py` are the current source of truth.

Every implemented formula/score in Asterion, audited honestly. Weak formulas are
**not hidden** — each carries a maturity flag:

- **production** — real inputs from SEC/XBRL, deterministic, trustworthy now.
- **mvp** — formula is reasonable but unvalidated/untuned, OR depends on an input
  (e.g. WACC) that is currently a fixed assumption.
- **placeholder** — the formula runs but is fed mock/hardcoded inputs; the output
  is currently meaningless per-ticker.

The single most important finding: **the five "advanced scores" in the generated
valuation scorecards are fed identical hardcoded mock inputs across all tickers**
(`AdvancedInputsFetcher.fetch_m2_ratios` / `fetch_m3_rag_data` return constants).
So NVDA, META, MSFT, MU, … all show `expectations_gap=75`, `thesis_fragility=80`,
`operating_leverage_convexity=70.25`. The deterministic *financial ratios* and
*forensic scores* are real; the *advanced 0–100 scores* are not yet wired to real
per-ticker data. The M9 backtest (reports/backtest_summary.md) demonstrates this
empirically — zero score variance across the book.

---

## 1. M2 Financial Ratios — `app/quant/fundamentals.py`

All share the `FormulaResult` contract (value, inputs, confidence 0–1,
missing_flags, source_fact_ids). Pure functions. Safe division everywhere
(`_safe_div` → None on zero/None denominator). Missing input ⇒ value None,
confidence 0.0. Zero denominator ⇒ value None, flag `zero_denominator`,
confidence 1.0 (math is valid, data degenerate). **Deterministic.**

| Name | Definition | Inputs | Source | Output range | Interpretation | Failure modes | Maturity |
|---|---|---|---|---|---|---|---|
| revenue_growth | (cur − prior)/abs(prior) | current/prior revenue | XBRL facts | ~−1 … +∞ | YoY top-line growth | zero prior, missing period | production |
| gross_margin | gross_profit / revenue | GrossProfit, Revenues | XBRL | 0 … ~1 (can be <0) | pricing power / COGS | zero revenue | production |
| operating_margin | operating_income / revenue | OperatingIncomeLoss, Revenues | XBRL | <0 … ~1 | core profitability | zero revenue | production |
| net_margin | net_income / revenue | NetIncomeLoss, Revenues | XBRL | <0 … ~1 | bottom-line margin | zero revenue | production |
| fcf_margin | (OCF − abs(capex)) / revenue | OCF, capex, revenue | XBRL | <0 … ~1 | cash conversion | zero revenue | production |
| roe | net_income / equity | NetIncome, StockholdersEquity | XBRL | unbounded | return on equity | zero/neg equity distorts | production |
| roa | net_income / total_assets | NetIncome, Assets | XBRL | unbounded | asset efficiency | zero assets | production |
| current_ratio | current_assets / current_liabilities | AssetsCurrent, LiabilitiesCurrent | XBRL | 0 … +∞ | short-term liquidity | zero liabilities | production |
| debt_to_equity | total_debt / equity | LongTermDebt…, equity | XBRL | unbounded | leverage | zero/neg equity | production |
| sbc_to_revenue | sbc / revenue | ShareBasedCompensation, revenue | XBRL | 0 … +∞ | dilution intensity | zero revenue | production |
| sbc_to_ocf | sbc / OCF | sbc, OCF | XBRL | unbounded | SBC vs cash | zero/neg OCF | production |
| shares_outstanding_change | (cur − prior)/prior | shares (dei/us-gaap) | XBRL | ~−1 … +∞ | dilution/buyback | zero prior, taxonomy miss | production |

**Confidence behaviour:** binary — 1.0 when all inputs present, 0.0 when any
missing. Orchestrator stores `missing_penalty = 1 − confidence` (scoring_inputs.py).

**Negative values:** allowed and meaningful (negative margins, negative growth).
Not clamped. ROE/ROA/D-E with negative equity produce mathematically valid but
interpretively misleading numbers — a known caveat, not flagged today.

---

## 2. Valuation Multiples — `app/quant/valuation.py`

Same `FormulaResult` contract. Confidence here is graded: `1 − 0.2·len(missing)`
(EV uses `1 − 0.1·len(missing)`). Market-cap-dependent ⇒ None without price data.
**Deterministic.**

| Name | Definition | Inputs | Output | Interpretation | Maturity |
|---|---|---|---|---|---|
| enterprise_value | mc + debt − cash | market_cap, total_debt, cash | $ | takeover value | production (needs market_cap) |
| ev_to_revenue | EV / revenue | EV, revenue | × | sales multiple | production |
| ev_to_ebitda | EV / EBITDA | EV, ebitda | × | cash-earnings multiple | production |
| pe_ratio | market_cap / net_income | mc, net_income | × | earnings multiple | production |
| pb_ratio | market_cap / book_value | mc, equity | × | book multiple | production |
| p_to_fcf | market_cap / FCF | mc, fcf | × | FCF multiple | production |
| fcf_yield | FCF / market_cap | fcf, mc | frac | inverse of P/FCF | production |
| earnings_yield | net_income / EV | ni, EV | frac | yield vs EV | production |

**Failure modes:** missing market_cap (no live price) collapses every
market-relative multiple to None — common, handled. Negative net income →
negative PE (valid but not meaningful); not specially flagged.

---

## 3. Forensic Scores — `app/quant/forensic.py`

**Deterministic.**

**Altman Z-Score** — `Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5`
(X1 WC/TA, X2 RE/TA, X3 EBIT/TA, X4 MktCap/TL, X5 Rev/TA). Hard-requires
total_assets and market_cap (no private-firm variant). Missing components count
as 0 in the sum but lower confidence (`available/5`). **Caveat:** scoring_inputs
passes *book equity* as the market_cap proxy (X4), so Z is conservative/biased
until real market cap is wired. Range ~ −5 … +10; <1.8 distress, >3 safe. mvp.

**Piotroski F-Score** — 0–9 integer over 9 binary criteria (profitability 4,
leverage/liquidity 3, efficiency 2). Needs current + prior period; missing
criterion is *not scored* (confidence = criteria_scored/9). Higher is stronger.
production.

**Accruals ratio** — `(NI − OCF)/TA`. More negative = higher earnings quality.
None on zero TA. production.

**Quality of earnings** — `OCF / NI`. >1 = cash exceeds reported earnings (good).
None on zero/negative NI edge. production.

---

## 4. Reverse DCF — `app/quant/reverse_dcf.py`

`implied_growth_rate(EV, FCF, discount_rate=0.10, terminal_growth=0.025,
horizon=10)`. Solves (Brent root-find, bracket −0.99…10.0) for the FCF growth `g`
that makes PV(explicit FCF) + PV(terminal, Gordon) = EV. Returns None when
FCF≤0, EV≤0, or discount≤terminal. **Deterministic** given inputs.

**Output:** implied annual growth (decimal). **Interpretation:** growth the
current price already demands. **Maturity: mvp.** Two gaps: (1) **discount_rate
is a fixed 10%** — no per-company WACC (see docs/25); (2) it is wired into the
expectations_gap score using mock inputs, not live EV/FCF, in the generated
scorecards.

---

## 5. Advanced 0–100 Scores — `app/scoring/advanced_scores.py`, `expectations_gap.py`, `thesis_fragility.py`

All clamp to 0–100, return `{score, confidence, inputs_used, missing_inputs,
explanation, failure_modes}`. Confidence = fraction of required inputs present.
**The functions are deterministic; the *inputs* are the problem.**

| Score | Definition | Required inputs | Direction | Maturity | Why |
|---|---|---|---|---|---|
| operating_leverage_convexity | 50 + gross_margin·100·rev_growth | gross_margin, revenue_growth_yoy | higher_is_better | **mvp** | unbounded, untuned; reasonable shape |
| reflexivity_risk | dte·20 + (2−min(cr,2))·20 | current_ratio, debt_to_equity | higher_is_risk | **mvp** | leverage/liquidity proxy; no price-feedback term — misnamed |
| expectations_gap | 50 + (implied−historical_growth)·250 | implied_growth, historical_growth_ttm | higher_is_risk | **mvp** | sound formula, fed mock growth + fixed-WACC DCF |
| thesis_fragility | dcf_sensitivity_impact·100 | dcf_sensitivity_impact | higher_is_risk | **placeholder** | input is a hardcoded constant, not the real sensitivity table |
| misunderstood_change | 50 + capex·100 − sentiment·50 | sentiment_shift, capex_growth | higher_is_better | **placeholder** | needs sentiment + capex feeds not ingested |
| perception_shift | 50 + revisions·50 + surprise·100 | analyst_revisions, earnings_surprise | higher_is_better | **placeholder** | needs analyst/surprise feeds |
| narrative_entropy | tone_var·50 + topic_disp·50 | management_tone_variance, topic_dispersion | higher_is_risk | **placeholder** | needs transcript NLP |
| crowding_risk | (registry only, unimplemented) | short_interest, inst_ownership | higher_is_risk | **placeholder** | P2, no impl |
| supply_demand_imbalance | (registry only) | float_turnover, insider_buying | neutral | **placeholder** | P2, no impl |
| deep_learning_price_predictors | (registry only) | tick_data, order_book | n/a | **excluded** | P3 — out of scope; no fake price prediction (per M9 brief) |

**Missing-data behaviour:** if all required inputs missing → score 50.0,
confidence 0.0, explanation "Cannot calculate …". Otherwise score computed on a
safe default for the missing input with confidence reduced proportionally — this
silently substitutes a default rather than abstaining, a behaviour worth
revisiting (it can produce a confident-looking 50 from one input).

**The mock-input pipeline:** `app/scoring/advanced_inputs.py::AdvancedInputsFetcher`
returns the SAME constants for every ticker (gross_margin 0.65, revenue_growth
0.15, etc.). Any scorecard generated through it carries identical advanced scores
regardless of company. **This is the #1 thing to fix before the scores mean
anything.** Calibration (`app/scoring/calibration.py`, M9) now records direction +
maturity for each so the UI can label them honestly and the weak ones are visible.

---

## 6. Deterministic Classification — `app/decision/policy_engine.py`

`evaluate_policy(ratios, advanced_scores, missing_data, …) → ScorecardOutput`.
Hardcoded rule cascade, **no LLM**. Order:

1. hallucination_failed → `insufficient_data`
2. >5 missing data points → `insufficient_data`
3. ≥2 structural red flags (dte>2, ROA<0, reflexivity>70) → `avoid_due_to_red_flags`
4. pe_ratio missing → `wait_for_valuation_data`
5. **pe>40 AND expectations_gap>70 → `valuation_risk_watchlist`**
6. pe>25 OR expectations_gap>50 → `wait_for_better_price`
7. quality test (gm>0.7, fcf>0.15, op_lev>70) → `quality_compounder_candidate`
8. else → `risk_review_required`

**Audit finding:** because expectations_gap is a constant 75 across the book,
rule 5 reduces to **pe>40 alone**. The classification is effectively a PE filter
wearing an expectations-gap label. Thresholds aren't "too strict/loose" so much
as **untested** — they've never been calibrated against outcomes (M9 backtest is
the first attempt, and it can't separate names because the scores don't vary).
**Maturity: mvp** (logic deterministic and sensible; thresholds uncalibrated).

---

## 7. Portfolio Risk Metrics — `app/portfolio/risk_metrics.py`, `policy_rules.py`

**Deterministic.** All weight-based, value = `current_value` or qty×price.

| Metric | Definition | Interpretation | Maturity |
|---|---|---|---|
| portfolio_value | Σ position values | total book | production |
| position_weights | value / total | single-name concentration | production |
| sector_concentration | Σ weight by asset_type | sector mix | production |
| theme_concentration | Σ weight by `notes` field | theme mix | **mvp** — themes parsed from a free-text notes string |
| speculative_exposure | Σ weight where notes∋"speculative"/"biotech" | spec sleeve | **mvp** — substring match on notes |
| core_etf_exposure | Σ weight where notes∋"core" | defensive floor | **mvp** — substring match |
| unrealized_pl_% | (current − cost)/cost | lifetime P/L | production (needs cost basis) |

**Daily contribution** — `app/api/routes/ui.py::compute_contributors`:
`contribution = current_value · (daily_change_pct/100)`, ranked, with an
`unexplained_difference = reported_daily_pnl − Σ contributions`. **Deterministic,
honest** (surfaces the residual). Maturity: production. Caveat: uses provider
`dp` (daily %); intraday timing differences create the residual it reports.

**Policy thresholds** (policy_rules.py): max single 15%, max theme 25%, max
speculative 10%, min core ETF 30%. Hardcoded constants — reasonable defaults,
**uncalibrated**. Theme/speculative/core depend on the `notes` text convention.

---

## Summary of weak spots (ranked)

1. **Advanced scores fed mock constants** (`AdvancedInputsFetcher`) — placeholders; fix first.
2. **thesis_fragility** input is a hardcoded constant — not connected to reverse-DCF sensitivity. Redesign.
3. **Reverse-DCF uses fixed 10% WACC** — needs per-company WACC (docs/25).
4. **operating_leverage_convexity / reflexivity_risk** — naive, unbounded/misnamed; calibrate or redesign.
5. **Classification thresholds + policy limits** — sensible but never calibrated against outcomes.
6. **Theme/speculative/core exposure** — rely on substring matching of a free-text notes field; brittle.
7. **Altman X4** uses book equity as a market-cap proxy — wire real market cap.

## What is trustworthy now

- All 12 M2 financial ratios + 8 valuation multiples (when market_cap present).
- Forensic: Piotroski F, accruals, quality-of-earnings (Altman with the equity-proxy caveat).
- Reverse-DCF *mechanics* (the solver is correct; the WACC/inputs are the gap).
- Portfolio value, weights, concentration, daily contribution with honest residual.

See `app/scoring/calibration.py` for machine-readable direction + maturity, and
`reports/backtest_summary.md` for the empirical demonstration.
