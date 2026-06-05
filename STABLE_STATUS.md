# Asterion — Stable Status

**As of:** 2026-06-05 · **Branch:** `main` @ `2302d7a` (clean, pushed) · **Tests:** 385 backend pass, frontend builds clean.

Snapshot of where Asterion stands before pivoting to the **Verifex + Asterion
decision-intelligence** theme. Feature work on Asterion is **paused** here.

---

## What works

- **Local-first research cockpit** — FastAPI backend + Next.js frontend, Postgres, optional Ollama. `make start` boots both.
- **SEC / XBRL ingestion** — rate-limited, full provenance on every fact.
- **Deterministic financial ratios** — no LLM arithmetic.
- **Forensic scores** — accrual, dilution, reflexivity, thesis-fragility, with confidence + provenance.
- **Reverse DCF + dynamic WACC** — CAPM with FRED risk-free + provider/sector beta, honest fallbacks.
- **Opportunity Scanner** — ranks the universe by a transparent composite (value/quality/safety/change). Two calibration layers:
  - *cross-sectional* screen score (percentile vs current scan — drives ranking),
  - *absolute* grade A–E (anchored to a pinned reference distribution — stable across scans).
- **IPO / private-company mode** — verifies an S-1 vs SEC EDGAR, parses with provenance, builds a research-only scorecard (scenario model for negative-FCF names, 7-category risk engine). Never invents numbers, no buy/sell.
- **Portfolio concentration risk + daily contribution analysis.**
- **Beginner / Pro UI** — progressive disclosure, onboarding.
- **Public demo mode** — `make demo`, no DB or keys (see below).

Core contract holds throughout: no buy/sell advice, missing data shown as missing, confidence degrades with missing inputs, every number traceable.

---

## How to run the demo

No Postgres, no SEC, no API keys. After cloning + installing backend venv and frontend deps:

```bash
make demo
```

Seeds `examples/demo/reports/` (21 public-company scorecards + SpaceX IPO + SEC verification) into `reports/`, pins the calibration profile, builds the scanner snapshot, starts both servers. Then open:

- <http://localhost:3000/scanner> — ranked screen (both calibration layers)
- <http://localhost:3000/ipo/SPACEX> — IPO / private-company mode
- <http://localhost:3000/reports> — generated scorecards

File-backed surfaces work immediately. Pages needing live market/portfolio data (market, portfolio, dashboard) show honest empty states until real data is ingested. Demo data only — no holdings, broker data, or secrets.

---

## Intentionally not finished

- **Absolute bands are not outcome-fitted.** Grade A–E is anchored to the *observed score distribution* (pinned), not to *forward outcomes*. The band rubric is documented, not empirically calibrated to realized results.
- **Demo covers file-backed surfaces only.** Market / portfolio / dashboard need a live DB + ingestion; they degrade gracefully rather than fake data.
- **IPO mode is hardwired to SpaceX (SPCX).** Not generalized to arbitrary S-1 URLs/tickers yet.
- **Provider integrations optional + partial.** Without FINNHUB/FRED/FMP keys, Asterion uses stored/fallback data (clearly labeled). No live beta/macro calibration across the whole universe yet.
- **Scanner/IPO capture spec screenshots only** (`frontend/tests/m13_capture.spec.ts`) — no visual-regression assertions.
- **Report exports are markdown/JSON scorecards** — no richer export formats.
- **No compliance / risk-disclosure layer.**

None of these are bugs — they are scoped-out edges, documented so the pivot doesn't trip over them.

---

## Next roadmap items (paused)

1. **Provider beta + macro calibration** — live FRED/FMP across the universe.
2. **Richer report exports.**
3. **Outcome-anchored calibration** — fit the absolute A–E bands to forward outcomes (needs a labeled backtest dataset).
4. **Optional compliance / risk layer.**

---

## Current main branch status

- `main` @ `2302d7a`, clean working tree, pushed to `origin/main`.
- All feature branches (`m13-ipo-calibration`, `m14-absolute-calibration`, `m15-public-demo`) merged and deleted — local + remote.
- 385 backend tests pass; frontend builds clean.
- **Asterion feature work paused here.** Next theme: **Verifex + Asterion integration / decision-intelligence layer.**
