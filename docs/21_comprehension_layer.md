# 21 — M8.9 Comprehension Layer + Simple/Terminal Mode

Date: 2026-06-04. Goal: make Asterion understandable in 5 seconds without losing
the terminal aesthetic. No redesign — an "understanding layer" on top of the data.

## What changed

- **Today's Portfolio Readout** (`components/portfolio/TodaysReadout.tsx`) — plain-English box above the chart on `/market` and at the top of `/dashboard`: portfolio status sentence, helped/hurt contributors, **Main risk**, **Next** action.
- **Why-did-it-move calc** — backend `GET /api/portfolio/contributors` (`api/routes/ui.py::compute_contributors`) returns per-holding `estimated_contribution_dollars = current_value × daily_change_pct/100`, ranked `top_positive`/`top_negative`, `sum_contributions`, and `unexplained_difference` vs reported daily P/L. Frontend mirror in `lib/insights.ts::computeContributors` as a 404 fallback.
- **Simple / Terminal toggle** (`components/ui/ViewMode.tsx`) — top-nav toggle, persisted in localStorage. Route default: `/market` → Terminal, everything else → Simple, until the user picks. `ModeGate` hides dense panels (heatmap, per-provider breakdown) in Simple mode.
- **Heatmap comprehension** — caption "Size = position value · color = today's % move" above; "Today's drag: … / Today's support: …" below.
- **Right rail regrouped** — Portfolio · Today's movers (helped/hurt) · Research queue (missing data, valuation risk, 3 latest reports + "view all") · Data status (live/polling badge, provider, last updated).
- **Chart purpose label** — selected ticker tagged "Market reference" (SPY/VOO/QQQ…) or "Portfolio holding", with a one-line explanation.
- **`/dashboard` is now the explain-my-portfolio page** — sections: Today's summary → Why it moved → Biggest risks → What to check next → Allocation snapshot → Missing data. Not terminal-dense.

## Top-contributor calculation example (demo book)

`/api/portfolio/contributors` on the demo book (`examples/sample_portfolio.csv`):

```
total_value          1400.00
daily_pnl_reported    -2.10
sum_contributions     -2.10
unexplained_difference 0.00
top_positive  MSFT +1.20 · V +0.40
top_negative  NVDA -2.50 · META -1.20
```

e.g. MSFT: 300.00 value × (+0.40% / 100) ≈ **+$1.20**. NVDA: 250.00 × (−1.00%/100) ≈ **−$2.50**.
Sum of all contributions equals the reported daily P/L exactly here (every
position is value-based), so `unexplained_difference` is $0.00.

## Tests

- Backend: `tests/api/test_contributors.py` — formula, ranking, sum/unexplained, missing-pct handling. **230 backend tests pass** (was 226).
- Frontend: `tests/m89.spec.ts` — readout visible, contributors helped/hurt visible, mode toggle visible, heatmap explanation visible, "Today's drag" visible, no buy/sell language; on `/dashboard` readout + "Why it moved today" + Main risk visible.

## Screenshots (`screenshots/`)

`final_dashboard.png` (Simple — readout + why-it-moved leads), `final_market_terminal.png`
(Terminal — readout above chart, heatmap caption + drag/support, regrouped rail),
`final_market_simple.png` (Simple market — heatmap + provider density hidden).

## Remaining limitations

1. Contributions are **estimates** from `daily_change_pct × current_value` — every position is `current_value_optional` (no shares), so this equals exposure-weighted move, not realized P/L. The UI says so.
2. `unexplained_difference` is non-zero only when some holding lacks a live quote; today it is $0.00.
3. Simple/Terminal default is route-based then a single global preference once toggled (not per-route persistence).
4. `/live` still uses the pre-terminal components.
