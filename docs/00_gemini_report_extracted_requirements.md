# 00 — Gemini Report: Extracted Requirements

**Status:** Phase 0 deliverable. Source = user-provided Gemini research report
("Institutional-Grade Equity Intelligence and Portfolio Decision Engine").
This file is the authoritative extraction. Asterion design downstream must trace
back to the items here, or consciously override them with a noted reason.

---

## 1. Key Takeaways

1. **No deterministic prediction.** Markets are noisy, reflexive, non-stationary,
   adversarial. The engine operates only in: probability estimation, expected
   value, uncertainty quantification, downside-risk measurement, and explicit
   thesis-invalidation conditions. Any "guaranteed alpha" framing is rejected.
2. **Determinism before AI.** Every score must be reproducible from SQL using
   standard math, with **no external API call at scoring time**. The LLM sits at
   the *very end* of the pipeline. Its only jobs: translate numeric outputs into
   prose, and extract/summarize filing text. It must never calculate ratios,
   predict prices, or emit numbers absent from structured data.
3. **Forensic-first fundamentals.** Strip GAAP distortions. DuPont (5-step),
   Beneish M-score, Altman Z-score, Piotroski F-score are core, not optional.
4. **Valuation is a range, never a point.** Scenario DCF + Reverse DCF (extract
   market-implied growth) + Earnings Power Value (EPV) as a hard floor + SOTP +
   relative multiples vs historical sector percentiles.
5. **Regime-awareness is structural.** A Hidden Markov Model classifies market
   state and re-weights the final ensemble (Quality/Value/Balance-Sheet dominate
   in bear/high-vol; Momentum/Growth dominate in bull/expansion).
6. **Day trading is a walled garden.** Structurally isolated at DB schema and UI
   routing levels. Fundamentals irrelevant intraday; order flow dictates. Hard
   capital caps, ATR trailing stops, mandatory journaling, explicit unreliability
   warnings.
7. **Bias prevention is non-negotiable.** Survivorship bias (retain delisted
   tickers via `is_active`), look-ahead bias (Purged Combinatorial CV / strict
   walk-forward), and mandatory slippage + transaction costs in every backtest.
8. **Tree models over deep nets** for tabular fundamentals (XGBoost / LightGBM /
   RF). SHAP for explainability. Deep nets explicitly de-prioritized.

---

## 2. Useful Formulas (verbatim from report, to be implemented deterministically)

### Fundamental / Forensic
- **5-step DuPont ROE** = TaxBurden × InterestBurden × OperatingMargin ×
  AssetTurnover × FinancialLeverage
  - TaxBurden = NetIncome / PreTaxIncome
  - InterestBurden = PreTaxIncome / OperatingIncome
  - OperatingMargin = OperatingIncome / Revenue
  - AssetTurnover = Revenue / AvgTotalAssets
  - FinancialLeverage = AvgTotalAssets / AvgShareholdersEquity
- **Beneish M-score** — 8 vars: DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA.
  Flag manipulator at **M > −1.78**; trigger mandatory human review at **−2.22**
  (more conservative). *(Note: higher M = more likely manipulator.)*
- **Altman Z-score** — entity-type dependent weights:
  - Private manufacturing: EBIT/TA multiplier = **3.107**.
  - Non-manufacturing / service: `Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4`
    (note the 6.72 multiplier on X3 = EBIT/TA).
- **Piotroski F-score** — 9 binary tests, score 0–9.
- **Rule of 40** (SaaS) = RevenueGrowthRate + FCFMargin.
- **FCF Yield**, **Cash Conversion Cycle**.
- **Dilution check**: SBC / Operating Cash Flow. Report flags when SBC subsidizes
  stated yields. Auto-fail dilution score (<10) when **SBC > 40% of OCF**.

### Valuation
- **Scenario DCF** — vary terminal growth + WACC → intrinsic value *range*.
- **Reverse DCF** — solve for market-implied growth rate. If implied perpetual
  growth **> WACC** (impossible), hard-cap valuation score at **20**.
- **EPV** = NormalizedAdjustedEarnings / WACC. Adjust for normalized tax,
  maintenance capex, excess depreciation. Strictly excludes growth. = value floor.
- **SOTP** for conglomerates.
- Relative multiples: EV/EBITDA, EV/Sales, P/E, P/FCF vs historical sector pctl.
- **Margin of Safety** = (IntrinsicValue − Price) / IntrinsicValue.

### Risk / Position Sizing
- **Continuous Kelly**: `f* = (μ − r) / σ²`. Enforce **fractional Kelly**
  (half / quarter) because equity returns are fat-tailed, not log-normal.
- **VaR**, **CVaR (95%)**, **Maximum Drawdown**, **Sortino**.
- **Black-Litterman**: market-equilibrium implied returns = Bayesian prior;
  update with system's quantitative views → posterior returns + covariance →
  allocation. Chosen over raw mean-variance (which over-concentrates).

### Momentum / Technical / Macro
- **Momentum score** = `CDF( (Return_12m − Return_1m) / (σ · √252) )`.
- VWAP (mean-reversion boundary), EMA, ATR, Bollinger (vol compression/expansion),
  volume-profile POC for support/resistance.
- **Macro sensitivity** = multiple-regression betas to DXY, 10Y yield, WTI.

---

## 3. Architecture Requirements

- **Frontend:** Next.js (SSR, financial charting — Lightweight Charts).
- **Backend:** Python + FastAPI. Hard dependency on the quant ecosystem:
  `scikit-learn`, `statsmodels`, `scipy.optimize` (Kelly / Black-Litterman),
  `hmmlearn` (regime detection).
- **DB:** PostgreSQL relational core + **TimescaleDB** (OHLCV time-series) +
  **pgvector** (filing NLP embeddings). Redis = message broker.
- **Tasks:** Celery for async (daily prices, fundamentals fetch, EDGAR scrape).
- **Alerting:** Telegram Bot API via webhooks.
- **Walled garden:** investment vs intraday separation enforced at schema + UI
  routing levels.

> Asterion override note: report says external APIs at ingestion; Asterion adds a
> **local-first LLM layer (Ollama-first)** that the report under-specifies. The
> report's "LLM at the end" principle is preserved and strengthened.

---

## 4. Database Requirements (report's 17-table baseline)

`companies` (ticker PK, cik, name, sector, industry, market_cap, **is_active** —
survivorship), `tickers` (symbol-change / dual-listing map), `prices_daily`
(composite PK ticker+date, incl. adj_close, vwap), `fundamentals`, `ratios`
(pre-calculated, minimize runtime), `sec_filings` (accession PK, form_type,
extracted_risk_text, **vector_embedding**), `scores` (historical — enables
self-backtesting of predictions), `catalysts`, `portfolio_positions` (entry,
size, kelly_fraction, atr_stop_loss), `trade_journal`, `backtests`.

Asterion expands this baseline substantially (see `06_database_schema.md`) but
must preserve: survivorship `is_active`, historical `scores`, pre-computed
`ratios`, and the vector column on filings.

---

## 5. Scoring Requirements (16 deterministic scores, 0–100)

Cross-sectional normalization: Z-score → CDF, against **GICS sector peers**.
Missing data → sector-median imputation **+ reduced confidence interval**.

| # | Score | Core inputs (report weighting) |
|---|-------|-------------------------------|
| 1 | Fundamental Quality | 0.40·Z(ROIC−WACC) + 0.30·Z(FCF_Conv) + 0.20·(Piotroski/9) + 0.10·Z(OpMargin). Utilities/Financials → ROE not ROIC. |
| 2 | Valuation Attractiveness | 0.40·Z(DCF_Margin) + 0.30·Z(EPV_Margin) + 0.20·Z(FCF_Yield) − 0.10·Z(EV/EBITDA_premium). REITs → P/AFFO. Reverse-DCF impossible → cap 20. |
| 3 | Growth Durability | 0.50·Z(Rev_CAGR) + 0.30·Z(GrossProfit_CAGR) − 0.20·σ(RevGrowth). SaaS → Rule of 40. |
| 4 | Balance Sheet Safety | 0.50·Z(Altman) + 0.30·Z(InterestCov) − 0.20·Z(NetDebt/EBITDA). Service → Z''. |
| 5 | Profitability | 0.40·Z(CROA) + 0.30·Z(OpMargin) + 0.30·Z(GrossProfit/Assets). Penalize if OCF missing. |
| 6 | Momentum | CDF((Ret12m−Ret1m)/(σ·√252)). Sector + mktcap normalized. |
| 7 | Technical Setup | VWAP distance, BB width, RSI, MACD hist, distance to volume-profile POC. |
| 8 | Catalyst | (1/Days_remaining) × EventImportance(0.1–1.0). |
| 9 | Sentiment | 0.50·TranscriptPolarity − 0.50·RiskFactorExpansionPenalty. |
| 10 | Risk | f(36m beta, 90d vol, mkt correlation); inverted so high=stable. |
| 11 | Downside Risk | 0.40·Z(Sortino) − 0.40·Z(MaxDD) − 0.20·Z(CVaR). |
| 12 | Dilution Risk | f(3y share CAGR, SBC/OCF); **auto-fail <10 if SBC>40% OCF**. |
| 13 | Macro Sensitivity | normalized |regression betas| to DXY, 10Y, WTI. |
| 14 | Insider/Institutional | 0.60·Z(net insider buys, ex-10b5-1) + 0.40·Z(13F delta). |
| 15 | **Final Investment** | ensemble of 1–14, **HMM regime-weighted**. |
| 16 | **Final Trading Setup** | gap%, RVOL, float, short interest. **Walled off.** |

**Decision matrix (report):** Research More · Add to Watchlist · Initiate Small
Starter · Wait for Better Price · Avoid · Exit/Reduce. (Asterion extends this set
— see `MASTER_PLAN.md`.)

---

## 6. Risk Warnings (must be enforced in code)

1. **Look-ahead bias** — financial series are highly autocorrelated. Standard
   randomized train/test leaks future data → "flawless in test, collapses live."
   Use Purged Combinatorial CV or strict walk-forward.
2. **Survivorship bias** — retain delisted assets in `companies` (is_active=false).
3. **Slippage + transaction costs** — mandatory in every backtest.
4. **Mean-variance instability** — hypersensitive to return inputs → use
   Black-Litterman.
5. **Kelly fragility** — continuous Kelly assumes log-normal; equities are
   fat-tailed → fractional Kelly, hard caps, no risk-of-ruin.
6. **SEC rate limits** — <10 req/s semaphore, compliant User-Agent
   (org name + email), exponential backoff, else IP ban (HTTP 429).
7. **News dedup** — syndicated identical articles skew sentiment → NLP dedup.
8. **Intraday unreliability** — explicitly warn the user; cap capital.

---

## 7. What Is Realistic (keep)

- Deterministic forensic + valuation + risk math from structured data. ✅
- Sector-relative normalization with confidence penalties for missing data. ✅
- Scenario/Reverse DCF + EPV as a *range*, never a point target. ✅
- HMM regime classification as a re-weighting layer (not a price predictor). ✅
- Black-Litterman + fractional Kelly for sizing. ✅
- RAG over SEC filings for risk-factor diffing + tone extraction. ✅
- Telegram alerts driven by deterministic triggers. ✅
- Self-backtesting of historical `scores`. ✅

---

## 8. What Is Unrealistic / Overhyped (downgrade or guard)

- **"Probability of benchmark outperformance"** as a single Final Investment
  number — keep the *score*, but present it as a relative ranking + confidence,
  **not** a literal probability, unless/until calibrated against realized
  outcomes (Brier score). Until then it is a heuristic, labeled as such.
- **HMM regime detection** is genuinely useful but fragile/regime-lagging on a
  solo-dev data budget. Ship a transparent rules-based regime (VIX / yield-curve /
  trend) as the **default**, HMM as an opt-in experimental module.
- **Black-Litterman** needs a credible covariance estimate + equilibrium weights;
  with ~20 tickers and limited history this is noisy. MVP: volatility-based and
  fractional-Kelly sizing first; BL behind a flag.
- **NLP "sentiment polarity → score"** from a small local model is noisy. Treat
  sentiment as *low weight*, always cite the exact extracted sentences, never let
  it dominate the verdict.
- **Multi-API stack (Alpaca + Polygon + FMP + Finnhub + Benzinga + SeekingAlpha)**
  is cost/complexity heavy for an MVP. Start with **free/low-cost only**: SEC
  EDGAR + FRED + one OHLCV source + user uploads. Everything behind a swappable
  provider interface.
- **Alternative data (GitHub commits, app rankings, patents)** — explicitly out
  of MVP scope (report agrees: "low priority").
- **Intraday / day-trading module** — keep walled and experimental; do **not**
  build live execution. Paper only.

---

## 9. How Asterion Implements This Safely

1. **Local-first core, APIs as pipes.** Postgres+pgvector+Timescale local;
   Ollama local LLM; APIs only ingest raw data. (Report's stack, plus local LLM.)
2. **Deterministic quant engine is the skeleton** (`backend/app/quant/`). Every
   formula = pure Python, typed, unit-tested, missing-data aware. No LLM math.
   Each score stores: raw inputs, formula version, confidence, missing-data
   penalty, explanation, source citations. Fully reproducible.
3. **LLM is the analyst, not the oracle.** Strict-JSON outputs, schema-validated,
   every numeric claim audited against the evidence pack / structured data; any
   un-sourced number is flagged. (`backend/app/llm/`, hallucination audit.)
4. **Walled garden enforced in schema + routing.** Separate score #15 (invest)
   and #16 (trade); separate tables; separate UI routes; capital caps.
5. **Bias guards in the backtester by construction** — delisted retention,
   purged/walk-forward CV, mandatory slippage + costs, signal delay.
6. **Confidence everywhere.** Data completeness + filing age + ensemble spread →
   Low/Med/High confidence on every verdict. Calibrate later via Brier score.
7. **Anti-hype contract.** No buy/sell without confidence + key risks + thesis
   invalidation. Final Investment "score" labeled a heuristic ranking until
   calibrated. Intraday signals labeled experimental + capped.
8. **Legal/ethical.** No pirated copyrighted text. Knowledge library = original
   summaries, framework cards, public-domain + SEC + user-provided material only.

---

### Traceability
Downstream docs that consume this file:
`MASTER_PLAN.md`, `01_local_first_architecture.md`, `06_database_schema.md`,
`08_backtesting_and_evaluation.md`, and the scoring spec in
`backend/app/scoring/`.
