# 20 — Frontend Rebuild Completion Report

Date: 2026-06-04. Companion to the audit in `19_frontend_brutal_audit.md`. This
records what actually changed, what is proven by screenshots/tests, and what is
still limited. No vague adjectives — claims below map to artifacts.

## 1. Files rewritten / added

**Design system (new)**
- `frontend/tailwind.config.ts` — terminal palette (bg/panel/border/up/down/warn/accent), mono + ui font vars, tight radii.
- `frontend/src/app/globals.css` — terminal CSS variables, `.num` tabular-mono helper, slim scrollbars, `.terminal-grid`.
- `frontend/src/lib/format.ts` — `isNum/money/compactMoney/pct/pctFrac/num/score100/timeAgo/safeDate` (real-zero vs missing aware).
- `frontend/src/components/ui/` — `Panel`, `PriceChange`, `MetricTile`, `Badges` (DataQuality/LiveMode/ProviderStatus/Classification), `TimeframeSelector` (+ChartTypeToggle), `States` (Empty/Error/LoadingSkeleton/ChartLoading), `MarketTopStrip`, `TerminalShell`.
- `frontend/src/components/charts/MarketPriceChart.tsx` — large responsive chart, line+candle, timeframe (1D–ALL), crosshair, provider header.
- `frontend/src/components/market/` — `MarketHeatmap`, `MarketTerminal`.
- `frontend/src/components/portfolio/` — `HBar`, `PortfolioTable` (sortable, row-click).

**Pages rewritten**
- `app/layout.tsx` — Inter+JetBrains Mono, `TerminalShell` (market strip + slim top nav) replaces the 256px admin sidebar.
- `app/page.tsx` — redirects `/` → `/market`.
- `app/market/page.tsx` (**new**) — Market Terminal.
- `app/dashboard/page.tsx` (**new**) — Portfolio Intelligence.
- `app/ticker/[ticker]/page.tsx` — rebuilt; all audited data bugs fixed.
- `app/portfolio/page.tsx` — brokerage table.
- `app/risk/page.tsx` — plain-English diagnosis.
- `app/coverage/page.tsx`, `app/reports/page.tsx`, `app/reports/[name]/page.tsx` — terminal restyle, `getApiBase()` instead of hardcoded `localhost`.
- `app/system/page.tsx` (**new**) — provider status panel.

**Backend (provider env support only — no new features)**
- `core/config.py` — added `OPENFIGI` alias resolution (finnhub/fmp/fred/polygon already aliased).
- `api/routes/system.py` — `openfigi` added to `ENV_HINTS` and the providers payload.

## 2. Old components replaced / left in place

- **Replaced in the live routes:** `Sidebar`, `ResearchDashboardClient`, `PriceChart`, `PortfolioLiveTable`, `HoldingsBarChart`, `ThemeBarChart`, `ThemePieChart`, `TooltipHint` are no longer imported by the rebuilt pages.
- **Left in place (still used by `/live`):** `LiveMonitorClient`, `LivePriceChart`, `LiveMarketStrip`, `useLiveQuotes`, `StreamDebugPanel`. The `/live` tick-by-tick monitor was out of scope for this pass and kept working as-is. The old files were not deleted to avoid breaking `/live`; they can be pruned when `/live` is folded into the terminal.

## 3. Audited bugs fixed (verifiable on `/ticker/PLTR`)

| Audit § | Bug | Fix |
|---|---|---|
| 4.1 | EV/FCF & EV/EBITDA hardcoded "Why is this missing?" | Removed; only metrics present in the scorecard are shown; absent ones read "not in scorecard". |
| 4.2 | Implied Growth read wrong path → always missing | Now reads `advanced_scores.expectations_gap.inputs_used.implied_growth` → renders **25.00%** for PLTR. |
| 3.1 | Score scale chaos ("80/10") | All advanced scores render on one `X / 100` scale via `score100()`. |
| 4.3 | `"Why is this missing?x"` | Units only appended to real values. |
| 5.4 | Hardcoded `localhost:8000` | All pages use `getApiBase()`. |
| 6 | Real `0` shown as missing | `isNum()` guards distinguish `0` from absent (Debt/Equity shows **0.00**). |

## 4. Providers actually active (observed live, 2026-06-04)

- **Finnhub — ACTIVE and real-time.** Key configured (masked `****2690`). `GET /api/market/quote/MSFT?debug=true` → `provider_used:"finnhub"`, `is_realtime_or_delayed:"realtime"`. Market strip (SPY $754.24) is finnhub-sourced.
- **Finnhub WebSocket** — endpoint `/ws/quotes` is available server-side (key present, `live_stream.mode = finnhub_ws`). The `/live` page consumes it. Static screenshots cannot prove streaming ticks; REST real-time is proven.
- **yfinance** — fallback, delayed; used per-symbol when finnhub returns empty (e.g. some illiquid tickers).
- **fmp / fred / polygon / openfigi** — not configured (no keys). Shown honestly as `not_configured` with the exact env vars to set. No raw key is ever sent to the client — only a masked suffix.

## 5. Screenshots (`screenshots/`, captured via Playwright at 1600×1000)

`final_market_terminal.png` · `final_dashboard.png` · `final_ticker_PLTR.png` ·
`final_portfolio.png` · `final_risk.png` · `final_coverage.png` · `provider_status.png`.

They show: large central chart with timeframe + line/candle controls; market top
strip with real proxy quotes; portfolio heatmap; right intelligence rail;
portfolio total (demo book); provider status with masked key; no admin sidebar; no
"Why is this missing?"; no Invalid Date.

## 6. Build / test status

- `npm run build` — ✅ clean (12 routes, no type/lint errors).
- Backend `pytest` — ✅ **226 passed**.
- Playwright `tests/m9_assert.spec.ts` — ✅ 4 passed (chart visible; PLTR has no fake N/A and uses `/ 100`; system page masks the key and leaks no secret; portfolio has no Invalid Date).
- Playwright `tests/m9_screens.spec.ts` — ✅ 7 screenshots.

## 7. Remaining limitations

1. **`/live`** still uses the old components and old color classes; it works but is visually off-theme. Fold it into the terminal in a follow-up.
2. **Intraday (1D/5D)** depends on the provider; when history is close-only or empty the chart says so honestly instead of faking ticks. Candles need OHLC; close-only data falls back to a line with a visible note.
3. **Market strip uses ETF/futures proxies** (SPY/QQQ/DIA/IWM/GLD/BTC-USD/BZ=F), labelled as proxies — index symbols (^GSPC) aren't on the finnhub free tier.
4. **Portfolio P/L is value-based**, not realized — every position lacks a share count (`cost_basis_missing`); the UI states this rather than implying brokerage P/L.
5. Backend WS live streaming is not asserted by an automated test here (REST real-time is).

## 8. Readiness

The product-experience correction the user asked for is done: a finance terminal
(market strip + large chart + heatmap + intelligence rail + honest provider/live
status), with the ticker data bugs fixed and proven by tests + screenshots. This
is a solid base for M9; the `/live` merge and intraday/candle depth are the next
increments.
