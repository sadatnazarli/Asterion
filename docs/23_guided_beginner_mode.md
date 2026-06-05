# M8.11 — Guided Beginner Mode

Goal: make Asterion usable by a non-professional investor. Not a redesign — an
onboarding and explanation layer on top of the M8.10 visual system. No backend
features, no Verifex, no new scoring, no portfolio math changes.

## What was added

### 1. Beginner / Pro toggle (default Beginner)
- Reused the existing `ViewMode` (`simple` / `terminal`) context, relabelled to
  **Beginner** / **Pro** (`MODE_LABEL`). `routeDefault()` now returns `simple`
  everywhere, so every page opens in Beginner mode on first visit.
- New `BeginnerOnly` / `ProOnly` client wrappers gate server-rendered children.
  Pro mode keeps the dense terminal (all guidance hidden); Beginner adds the
  explanation layer on top of the same panels.
- Toggle lives in the header (`data-testid="mode-toggle"`), persisted to
  `localStorage["asterion-view-mode"]`.

### 2. Onboarding walkthrough (first launch)
- `OnboardingModal` — 5 steps (Dashboard / Market / Portfolio / Risk / Ticker),
  each with a chip, one-line "what this page is for", and an "Open …" deep link.
  Back / Next / Skip / Done + progress dots. Dismissable
  (`data-testid="onboarding-dismiss"`); flag stored in
  `localStorage["asterion-onboarded"]` so it never re-shows.
- A persistent **Guide** button (`data-testid="guide-button"`) in the header
  re-opens the walkthrough on demand (custom `asterion:open-guide` event).

### 3. "Read this page in this order" (dashboard)
- `ReadingOrder` — 4 numbered steps: today's P/L → who helped/hurt → biggest
  risk → what to do next. Beginner-only, sits above the readout.

### 4. "What this means" explanations
- `MetricTile` gained `help` (a `?` tooltip beside the label, both modes) and
  `explain` (a plain faint sentence below the value, Beginner-only).
- Applied to the major metrics: Total value, Today P/L, Core ETF exposure,
  AI/semiconductor exposure, Total P/L (cost-basis), etc.

### 5. Per-page help boxes
- `HelpBox` — accent-stripe "This page answers: …" box, Beginner-only at each
  call site:
  - `/dashboard` — "What happened to my portfolio today?"
  - `/market` — "Is the whole market moving, or only my holdings?"
  - `/portfolio` — "Where is my money?"
  - `/risk` — "What could hurt me?"
  - `/ticker` — "Is this company strong, risky, or overpriced?"
  - `/coverage` — "How complete is Asterion's data on each holding?"

### 6. `?` tooltips for technical terms
- `glossary.ts` — plain-English definitions for: valuation risk, expectations
  gap, thesis fragility, RAG, memo, CIK, SEC facts, current value, weight, daily
  contribution, live provider, core ETF exposure, AI/semiconductor exposure,
  total value, today P/L, data quality, cost basis. `define(term)` =
  case-insensitive lookup.
- `HelpTip` (`?` button, hover/focus/click popover, `role="tooltip"`) +
  inline `Term`. Wired into MetricTiles, the PortfolioTable headers, the Risk
  "Valuation risk" card, the Coverage column headers, and the ticker scorecard
  rows (thesis fragility, expectations gap).

### 7. "Asterion explains" panel (dashboard)
- `AsterionExplains` — generates 4 plain sentences from the real numbers:
  whether the book is concentrated, whether core ETF is below the 30% target,
  which names drove today's move, and a "don't judge by one red day" caution.

### 8. "What should I do now?" checklist (dashboard)
- `ActionChecklist` — research-only steps with `☐` boxes and the explicit line
  **"Research steps only — Asterion never tells you to buy or sell."** No
  buy/sell language anywhere.

## Files

New: `lib/glossary.ts`, `ui/HelpTip.tsx`, `onboarding/HelpBox.tsx`,
`onboarding/DashboardGuides.tsx` (ReadingOrder / AsterionExplains /
ActionChecklist), `onboarding/OnboardingModal.tsx`, `tests/m8_11.spec.ts`.

Modified: `ui/ViewMode.tsx` (Beginner/Pro + BeginnerOnly/ProOnly),
`ui/MetricTile.tsx` (help/explain), `ui/Panel.tsx` (testId),
`ui/TerminalShell.tsx` (Guide + modal mount), `app/dashboard/page.tsx`,
`market/MarketTerminal.tsx`, `app/portfolio/page.tsx`,
`portfolio/PortfolioTable.tsx`, `app/risk/page.tsx`,
`app/ticker/[ticker]/page.tsx`, `app/coverage/page.tsx`.

## Verification

- `npm run build` — clean, all routes compile (dashboard 2.43 kB, market 4.3 kB,
  portfolio 4.45 kB, risk 2.43 kB, coverage 2.43 kB, ticker 190 B).
- `npx playwright test m8_11` — **6/6 passed**: onboarding shows + dismisses +
  stays dismissed on reload; dashboard beginner help-box / reading-order /
  asterion-explains / action-checklist + no buy/sell + the "never tells you to
  buy or sell" line; tooltip hover reveals a definition; Pro mode hides the
  guidance; per-page help boxes across /market /portfolio /risk /ticker.
- Backend `pytest` — **230 passed** (backend untouched, confirmed).
- Screenshots (`screenshots/m8_11_*.png`): onboarding modal, dashboard beginner,
  market beginner, ticker beginner — all inspected, structure confirmed.

## Beginner-mode behaviour

Beginner is the default on every page. Each page leads with a one-line "this
page answers …" box, every technical term carries a `?` tooltip, and the major
numbers carry a plain sentence underneath. The dashboard additionally gives a
reading order, an "Asterion explains" plain-English summary, and a research-only
checklist. Flipping to Pro strips all of it back to the dense M8.10 terminal.

## Remaining confusing areas (honest)

- The ticker **Asterion scorecard (0–100)** still shows five advanced scores;
  only thesis fragility and expectations gap have tooltips. The other three
  (operating leverage convexity, reflexivity risk, misunderstood change) are
  unexplained for a beginner.
- The **Coverage matrix** dot grid is compact and information-dense; the help
  box explains the dots but the page is still oriented to power users.
- "Implied Growth (5Y)" (reverse-DCF) has no beginner explanation yet.
- Onboarding is text-only (no animated highlight of the actual UI region each
  step refers to).
