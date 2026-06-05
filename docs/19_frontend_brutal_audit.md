# 19 — Frontend Brutal Audit

Date: 2026-06-04. Scope: everything under `frontend/src`. Verdict up front:
**the current frontend is a generic dark admin panel, not a finance terminal.**
It uses the Inter font, `rounded-xl border bg-card p-6 shadow` SaaS cards
everywhere, a 64px-wide app sidebar, and 260px toy charts. It also ships
**real data bugs** that print "Why is this missing?" on top of values that exist
in the JSON. Below is the honest, file-by-file accounting and the rewrite list.

---

## 0. Evidence base

Backend API surface (verified from `backend/app/api/routes/*` + `market/router.py`):

| Endpoint | Returns |
|---|---|
| `/api/portfolio/live` | `total_value, daily_pnl, daily_pnl_pct, total_pnl, cost_basis_missing, holdings[]` |
| `/api/portfolio/latest` | raw `my_real_portfolio_report.json` (`summary, weights, positions, theme_concentration, policy_warnings, m6_scorecards_integrated`) |
| `/api/portfolio/coverage` | `{coverage: [...]}` per-ticker data-quality flags |
| `/api/tickers/{t}/valuation` | `classification, confidence, reason, metrics{}, advanced_scores{}, missing_data[], thesis_invalidation_triggers[], monitor_next[]` |
| `/api/tickers/{t}/scorecard` | M-score scorecard |
| `/api/market/quote/{t}` | finnhub shape `{c,d,dp,t,provider_used,cache_status,cache_age}` |
| `/api/market/history/{t}?range=` | `{history:[{t,c,...}]}` |
| `/api/market/sparkline/{t}` | `{sparkline:[...]}` |
| `/api/system/providers` | per-provider `configured,status,masked_key,last_success_at,setup_hint` |
| `/ws/quotes?tickers=` | finnhub WS or polling fallback |

Real data sample (`reports/PLTR_valuation_scorecard.json`): `metrics =
{gross_margin:0.81, fcf_margin:0.35, debt_to_equity:0.0, current_ratio:5.5,
pe_ratio:45.0}`; `advanced_scores` each 0–100 (`thesis_fragility:80,
expectations_gap:75, operating_leverage_convexity:70.25, reflexivity_risk:0`).
Portfolio (demo book): `total_value 1400.00`, **every
position `quantity:null, average_cost:null, value_source:"current_value_optional"`**.

---

## 1. What is confusing

1. **No clear entry point.** `/` is labelled "Research Cockpit" but mixes a
   market strip, portfolio totals, and an explainer box. The user asked for a
   *Market Terminal*; there is **no `/market` route at all**.
2. **Sidebar is an admin chrome pattern**, not a terminal top-strip. Finance
   terminals lead with a horizontal ticker tape; here nav eats 256px of width
   (`Sidebar.tsx:20` `w-64`) and pushes the (already small) chart right.
3. **"What does this dashboard mean?" prose box** (`ResearchDashboardClient.tsx:47`)
   is the loudest element on the page — explanation dominates data.
4. Two near-identical chart components (`PriceChart.tsx`, `LivePriceChart.tsx`)
   with copy-pasted bodies; unclear which is canonical.

## 2. What is ugly

1. **Generic SaaS cards everywhere**: `rounded-xl border border-border bg-card
   p-6 shadow` repeats ~20×. Soft corners + drop shadows = admin dashboard, not
   Bloomberg.
2. **Inter font** (`layout.tsx:6`) for numbers. Terminals use tabular monospace
   for price columns; here only ad-hoc `tabular-nums` in one place.
3. **Toy charts**: both chart components hard-code `height: 260` (`PriceChart.tsx:47`,
   `LivePriceChart.tsx:49`). Yahoo's chart is the page. Here it's a thumbnail.
4. **Zinc-on-zinc palette** (`tailwind.config.ts`): `bg #09090b`, `card #18181b`,
   `border #27272a` — no real green/red/amber semantic system; price color is
   inline `text-green-500/text-red-500` ad hoc.
5. Wasted vertical space: every section is a full-width padded card stack;
   density is low, scroll is high.

## 3. What is misleading

1. **Score scale chaos — this is the "80 / 10" complaint.** All advanced scores
   are 0–100, but the ticker page labels them inconsistently
   (`ticker/[ticker]/page.tsx`):
   - `thesis_fragility` → `"80.00 / 100"` (line 87) ✅
   - `expectations_gap` → `"75.00"` (line 149) — no scale
   - `operating_leverage_convexity`, `misunderstood_change`, `reflexivity_risk`
     → raw number, no scale, no direction.
   `reflexivity_risk:0` renders as a bare `"0.00"` — for a *risk* score 0 = good,
   but unlabelled it reads like a broken/empty field.
2. **`current_value_optional` shown as live P/L.** `/api/portfolio/live`
   synthesizes `daily_pnl` from `dp%` × static value because `quantity` is null
   for every holding (`ui.py:82-94`). The dashboard prints
   "Today it is up $X (Y%)" as if it were realized brokerage P/L.
3. **`total_pnl` is always null** (no cost basis) yet the dashboard never says so
   on the headline — only the Portfolio page surfaces `cost_basis_missing`.

## 4. Fake / static / broken chart & data

1. **Hardcoded "Why is this missing?" strings.** `ticker/[ticker]/page.tsx:121`
   and `:125` — the **EV/FCF** and **EV/EBITDA** rows are literal strings. They
   never read the JSON. They will say "missing" forever, even when data exists.
2. **Wrong JSON path.** Line 79 reads `vData.implied_growth`, but the value lives
   at `advanced_scores.expectations_gap.inputs_used.implied_growth` (0.25 for
   PLTR). The "Implied Revenue Growth (5Y)" tile is therefore **always** "missing"
   despite the data being present.
3. **`"Why is this missing?x"`** — line 133 does
   `pe_ratio?.toFixed(2) || 'Why is this missing?'` then appends `x`, so a missing
   PE prints the question text with a stray `x`.
4. **Chart timeframe is fake.** Ticker chart hard-codes `?range=1m` (line 29);
   there is no 1D/5D/6M/1Y/5Y selector anywhere. The "Price History (1 Month)"
   title is the only timeframe the UI can ever show.
5. **Line only, no candles.** `addLineSeries` only; no chart-type toggle.
6. **`LivePriceChart` paints the live tick onto the last *daily* bucket**
   (`LivePriceChart.tsx:84`) — intraday movement collapses onto one day's point.

## 5. API data fetched but not used / mis-fetched

1. `quote.provider_used`, `cache_status`, `delayed` are returned by
   `/api/market/quote` but **never shown** next to a price. User cannot tell if a
   number is finnhub-real, yfinance-delayed, or stale cache.
2. `valuation.confidence`, `.reason`, `.thesis_invalidation_triggers`,
   `.monitor_next`, `.red_flags` exist in every scorecard JSON and are **not
   rendered** on the ticker page.
3. `metrics.fcf_margin` and `metrics.debt_to_equity` exist; the ticker table
   shows neither (and shows two hardcoded-missing rows instead).
4. **`localhost:8000` hardcoded** in `ticker/[ticker]/page.tsx:6,16,26` instead
   of `getApiBase()` from `lib/api.ts` — breaks the env override the rest of the
   app respects.

## 6. Where "N/A" / "missing" appears incorrectly

- EV/FCF, EV/EBITDA: always (hardcoded, §4.1).
- Implied Revenue Growth: always (wrong path, §4.2).
- Any advanced score equal to a valid value still renders without scale, looking
  half-broken (§3.1).
- Note: the `x?.toFixed(2) || 'missing'` pattern is *not* a falsy-zero bug
  (`(0).toFixed(2)` is the truthy string `"0.00"`), but it **is** fragile and the
  appended units (`x`, `%`) leak onto the fallback string.

## 7. Provider status clarity

- `/api/system/providers` only branches on `finnhub`; `fmp/fred/polygon` blocks
  exist server-side but **no UI surfaces them**. There is no `/system` or provider
  panel page. The dashboard reduces all of this to one yellow line: "Add
  FINNHUB_API_KEY…" (`ResearchDashboardClient.tsx:71`).
- `OPENFIGI_API_KEY` is not in `ENV_HINTS` at all (`system.py:8`).

## 8. Wasted space

- 256px permanent sidebar + `p-8` main padding + `max-w-7xl mx-auto` + per-section
  `space-y-8` cards = a lot of chrome around a little data. Right-hand market
  intelligence rail (watchlist, movers, reports) does not exist; that whole column
  of value is empty.

## 9. Where the user can't tell what to do next

- Dashboard "What should I check next?" is static text, not links to the actual
  missing-data tickers from `/api/portfolio/coverage` (which has exact
  `has_ratios/has_rag/has_memo` flags per ticker, currently unused on the home page).

## 10. Exact files to rewrite

| File | Action |
|---|---|
| `frontend/tailwind.config.ts` | Replace zinc palette with terminal tokens (bg/panel/grid/up/down/warn/neutral, mono font). |
| `frontend/src/app/globals.css` | Add terminal CSS variables + base type scale. |
| `frontend/src/app/layout.tsx` | Swap Inter→mono for numerics; replace sidebar shell with `TerminalShell` (top market strip + slim nav). |
| `frontend/src/components/Sidebar.tsx` | Replace/relegate; add `/market` as default. |
| `frontend/src/app/page.tsx` | Redirect `/` → `/market`. |
| **NEW** `frontend/src/app/market/page.tsx` + `components/market/*` + `components/charts/MarketPriceChart.tsx` + `MarketHeatmap.tsx` | Market Terminal (Phase 4). |
| `frontend/src/components/ResearchDashboardClient.tsx` | Rebuild as portfolio-intelligence dashboard (Phase 5). |
| `frontend/src/app/ticker/[ticker]/page.tsx` | Fix §4 bugs, add timeframe chart, render confidence/reason/triggers, use `getApiBase()`. |
| `frontend/src/app/portfolio/page.tsx` | Brokerage table: sortable, row-click, data-quality, value-source. |
| `frontend/src/app/risk/page.tsx` | Plain-English diagnosis from `policy_warnings` + concentration + valuation + coverage. |
| `frontend/src/app/coverage/page.tsx` | Keep matrix, restyle to terminal. |
| `frontend/src/app/reports/*` | Restyle list + markdown/json viewer. |
| **NEW** `frontend/src/components/ui/*` | TerminalShell, MarketTopStrip, ProviderStatusBadge, PriceChange, MetricTile, DataQualityBadge, TimeframeSelector, ChartPanel, HoldingsTable, RiskAlertCard, ResearchTaskQueue, ReportList, EmptyState, LoadingSkeleton, ErrorBanner. |
| `backend/app/api/routes/system.py` | Add `OPENFIGI`; expose richer provider state for the UI panel. |

Charts: keep `lightweight-charts` v4 (`addLineSeries`/`addCandlestickSeries`
valid), make the main chart fill its panel (≥ 420px, responsive), add timeframe +
type toggle, show price/change/provider header.

---

**Bottom line:** the failure is exactly as described — cards were added instead of
a terminal being built, and two ticker tiles lie about missing data. Phases 3–10
rebuild around a large central chart, a market strip, a heatmap, a right
intelligence rail, dense data, honest provider/live status, and correct field
mapping.
