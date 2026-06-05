# 08 — Backtesting & Evaluation

Trace: `MASTER_PLAN.md` §12 (M6), Phase 14, report §"Backtesting Rigor".
Principle: **build evaluation before trusting signals.** A score/memo is a
hypothesis until measured against realized outcomes with costs.

---

## 1. Non-Negotiable Guards (enforced by construction)

| Guard | How |
|-------|-----|
| **Look-ahead bias** | point-in-time data only; a backtest at date `t` may read no row with `retrieved_at`/`filing_date`/knowledge `> t`. Signal delay applied. |
| **Survivorship bias** | universe at `t` includes delisted tickers (`companies.is_active=false` retained); delisting handled as forced exit. |
| **Data leakage in CV** | **Purged + embargoed combinatorial CV** or strict **walk-forward**; never randomized splits on autocorrelated series. |
| **Costs** | mandatory transaction-cost model per trade. |
| **Slippage** | mandatory slippage model (spread/volume aware); low-liquidity penalized. |
| **Signal delay** | act on signal at next valid bar, not the bar that created it. |

## 2. Backtester Architecture (`backend/app/backtesting/`)

```
engine.py        walk-forward loop, point-in-time data access guard
universe.py      as-of universe incl. delisted (survivorship-safe)
costs.py         transaction cost + slippage models (from execution_assumptions)
cv.py            purged/embargoed combinatorial CV, walk-forward splitter
metrics.py       sharpe, sortino, calmar, max_dd, win_rate, expectancy, VaR/CVaR
rebalance.py     rebalance rules, position sizing hook (vol/Kelly)
evaluation.py    score-bucket + alert + memo + LLM evaluation
report.py        backtest_runs / backtest_trades / signal_performance writers
```

## 3. Metrics Reported (every run → `backtest_runs`)

Sharpe · Sortino · Calmar · Max Drawdown · win rate · expectancy · average return
after signal · CAGR · turnover · total costs paid. Per-trade rows → `backtest_trades`.

## 4. Signal / Score Evaluation

- **Score-bucket performance**: bucket `final_investment_score` (deciles); measure
  forward return at **7 / 30 / 90 days**, hit rate, average return → `signal_performance`.
- **Alert evaluation**: for each fired alert, forward return at 7/30/90d; track
  **false positives** and **missed opportunities**.
- **Calibration**: `final_investment_score` (and any probability) scored by
  **Brier score** + calibration curve. Until calibrated, the score is labeled a
  *ranking heuristic*, not a probability (`MASTER_PLAN.md` §14).
- **Day-trading setups evaluated strictly separately** (`trade_setups` /
  `paper_trades`), never blended into investment stats. Experimental label kept.

## 5. LLM / RAG Evaluation (the AI audit)

| Metric | Definition | Store |
|--------|-----------|-------|
| Hallucination rate | % outputs with `flagged_numbers` (number absent from evidence/structured) | `hallucination_audits` |
| Citation accuracy | % claims with a valid resolvable citation | `hallucination_audits` |
| Retrieval hit-rate | labeled-query relevant-chunk recall@k | eval set |
| Decision accuracy by category | verdict class vs realized outcome | `prediction_outcomes` |
| Memo outcome | did the thesis-invalidation trigger fire as written | `investment_journal` |

## 6. Prediction Outcome Loop

Each scoring pass can register a `model_prediction` (e.g., "top-decile, 90d
horizon"). After the horizon, `prediction_outcomes` records realized result +
Brier + correct flag. This is the system **backtesting its own past predictions**
(report: historical `scores` table enables this).

## 7. ML Models (when added, post-MVP)

Tree ensembles (XGBoost/LightGBM/RF) for tabular fundamentals; SHAP for feature
importance; out-of-sample via purged CV/walk-forward only. No deep nets in scope.
Feature importance must be economically logical or the feature is dropped.

## 8. Foundation-Pass Status

This pass delivers the **contract + module map only**. The walk-forward engine,
cost/slippage models, and evaluation writers are implemented in M6. Skeleton files
are created with the interfaces above so later work has a fixed target.
