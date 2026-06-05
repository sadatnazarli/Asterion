# 02 — Knowledge Library Overview

> The heart of Asterion is **not** the LLM. The heart is the knowledge library.

Trace: `MASTER_PLAN.md` §6. Split rule everywhere:
- **SQL (structured)** = numeric, comparable, score-feeding, audited.
- **Vector docs** = prose: philosophy, summaries, framework cards, filing chunks.
- **Never the LLM** = the actual numbers, thresholds, or score arithmetic.

Legal: no copyrighted full text. Original summaries, framework cards, citation
metadata, public-domain / SEC / user-provided material only.

---

## The 14 Libraries

For each: purpose · sources · storage (SQL vs vector vs JSON file) · update ·
retrieval · LLM use · never-LLM.

### 1. Investor Philosophy Library
- **Purpose:** structured lenses (Buffett, Graham, Lynch, Marks, Burry…) to
  evaluate a company from multiple disciplined viewpoints.
- **Sources:** original summaries of public interviews, letters (legally
  available), public-domain texts. No copyrighted books.
- **Storage:** JSON files `knowledge/investor_lenses/{slug}.json` (canonical) →
  mirrored to SQL `investor_lenses` + embedded for retrieval. `index.json` maps
  styles → slugs.
- **Update:** manual / curated; versioned in git.
- **Retrieval:** by style tag (value, quality, macro, growth, forensic,
  contrarian, quant, activist, short-seller, risk-manager) + vector similarity.
- **LLM use:** apply a lens to a company's scores+evidence; produce a lens verdict.
- **Never-LLM:** invent a lens's rules or thresholds.

### 2. Mathematical Finance Library
- **Purpose:** formula cards — the deterministic backbone.
- **Sources:** standard public finance/quant definitions; original wording.
- **Storage:** JSON `knowledge/formulas/{category}/{slug}.json` (card) +
  Python impl in `backend/app/quant/formulas/` + SQL `formula_cards` mirror.
- **Update:** versioned; each card names its `python_function_name`.
- **Retrieval:** by category/slug; cards shown in UI + cited in explanations.
- **LLM use:** explain a formula's meaning in prose.
- **Never-LLM:** compute the formula. Python only.

### 3. Valuation Library
- DCF/Reverse DCF/EPV/SOTP/multiples cards (subset of #2, category `valuation`)
  + per-sector valuation method mapping (links to #9). SQL + JSON.

### 4. Accounting & Forensic Analysis Library
- Beneish, Altman, Piotroski, accruals (Sloan), earnings-quality cards +
  thresholds + sector exclusions. Category `accounting_quality`/`solvency`. SQL.

### 5. Risk Management Library
- Beta, vol, Sharpe/Sortino/Calmar, VaR/CVaR, drawdown, tracking error cards +
  portfolio-level limits (sector concentration, factor exposure). SQL.

### 6. Portfolio Construction Library
- Kelly/fractional-Kelly, mean-variance, Black-Litterman, risk parity, ERC,
  vol/ATR sizing, Monte Carlo cards. SQL + JSON.

### 7. Market Regime Library
- HMM, VIX regime, yield-curve regime, inflation/rate regime, risk-on/off, sector
  rotation. Defines regime → score-weight maps consumed by Final Investment score.
- **Storage:** SQL `regime_definitions` + weight tables; rules-based default,
  HMM experimental.

### 8. Technical / Microstructure Library
- SMA/EMA/RSI/MACD/Bollinger/ATR/VWAP/RVOL/volume-profile/ORB/gap cards +
  intraday-only flags. Category `technical`/`daytrading_risk`. SQL.

### 9. Sector Playbook Library
- **Purpose:** per-sector which metrics matter / are dangerous, valuation method,
  catalysts, traps, score adjustments. **Drives sector-relative normalization.**
- **Storage:** JSON `knowledge/sector_playbooks/{slug}.json` → SQL
  `sector_playbooks`. See `05`→ scoring uses `scoring_adjustments`.
- **LLM use:** narrate sector context. **Never-LLM:** set the adjustments.

### 10. Company Knowledge Library
- **Purpose:** per-ticker profile (business model, segments, moat, capital
  allocation, dilution, bull/bear/risks, monitoring triggers).
- **Storage:** structured fields → SQL `company_knowledge_profiles`; text-heavy
  (10-K/10-Q/earnings summaries) → `raw_documents` + vector chunks. JSON template
  in `knowledge/company_profiles/_template.json`.
- **Update:** on new filing / earnings; `last_updated` stamped.

### 11. Decision Playbook Library
- **Purpose:** deterministic IF→THEN rules mapping scores+flags → verdict class.
- **Storage:** JSON `knowledge/decision_playbooks/*.json` → consumed by
  `backend/app/decision/`. SQL `decision_playbooks` mirror for audit.
- **Never-LLM:** the rules are code/config, not model output.

### 12. Backtest Memory Library
- **Purpose:** what score buckets / signals actually worked, with costs.
- **Storage:** SQL `backtest_runs`, `signal_performance`, `prediction_outcomes`.
- **Use:** feeds confidence + decision; never overwritten retroactively.

### 13. User Investment Journal Library
- **Purpose:** user theses, decisions, rationale, outcomes.
- **Storage:** SQL `investment_journal`, `user_decision_feedback`.

### 14. Mistake Pattern Library
- **Purpose:** recurring user/system errors (chasing momentum, ignoring dilution,
  averaging down on broken thesis…).
- **Storage:** SQL `mistake_patterns`; surfaced as warnings in decisions/alerts.

---

## What Is Structured vs Vector vs File (summary)

| Content | Home |
|---------|------|
| Numbers, ratios, scores, thresholds, limits | **SQL** |
| Investor lenses, formula cards, sector playbooks, decision rules | **JSON files (canonical) + SQL mirror** |
| Filings, transcripts, summaries, prose memos | **raw_documents + pgvector chunks** |
| Score arithmetic | **Python only** |

## Retrieval Contract

Every retrieved knowledge item carries provenance (source, url/file, license,
hash, version) so the LLM and UI can always cite it. See `03_rag_design.md`.
