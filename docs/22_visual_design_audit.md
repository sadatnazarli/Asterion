# 22 — Visual Design Audit (M8.10)

Date: 2026-06-04. Scope: **visual only**. No backend, no new features, no math
changes. The product logic from M8.9 is good; the surface still reads as a
"developer dashboard pretending to be a terminal." This is the brutal pass that
the token + component rebuild in this milestone is built against.

## 1. Why it feels uncomfortable

- **Every panel is a hard-bordered box.** `border border-border bg-panel` is
  stamped on literally everything — readout, chart, heatmap, rail cards, tables.
  The eye sees ~10 equally-weighted rectangles per screen and can't find the
  primary object. Bloomberg/Koyfin separate modules with *elevation and
  whitespace*, not a 1px cage around each one.
- **Border contrast is too high.** `#1e2630` borders on a `#0a0e14` background
  are clearly visible grid lines. Premium terminals use near-invisible hairlines
  (~6% white) and let a slightly-lighter panel fill do the separating.
- **The blue is loud and a little toy-like.** `#2f81f7` is a saturated SaaS blue.
  It's used for the active nav pill, the whole Today's-Readout background tint
  (`bg-accent/5` + `border-accent/30`), timeframe active state, links, and arrows
  — so the most "shouting" color is everywhere instead of reserved for "this is
  active / clickable."

## 2. Why it does not feel premium

- No elevation language. Flat `#0f141c` panels on `#0a0e14` bg — the 4-point
  delta is too small to read as depth, so borders do all the work and it looks
  like a wireframe.
- Greens/reds are crypto-exchange neon (`#16c784`, `#ea3943`). Institutional
  surfaces use calmer, slightly desaturated up/down so a red day doesn't feel
  like an alarm.
- Headers are weak: `text-2xs uppercase` muted labels are fine, but there's no
  type scale rhythm — body, labels, and numbers all sit around the same size, so
  nothing feels authored.

## 3. Which components look amateur

- **TodaysReadout** — full blue wash + blue border = the single most "demo app"
  element. Should be the calmest, most authoritative panel, separated by a thin
  accent stripe, not a colored box.
- **MetricTile** — bordered box per metric; four of them in a row look like form
  fields, not a stat strip.
- **MarketHeatmap** — flexbox mosaic with `gap-px bg-border` produces visible
  gutters and ragged right edges; labels are plain; intensity ramp tops out too
  bright.
- **MarketTopStrip** — tall (`py-1.5` + two lines) with a hard right border per
  cell; reads like a row of buttons, not a ticker tape.
- **Badges** — every badge is `border + bg/10 + text` (three colored properties);
  stacked they vibrate.

## 4. Which spacing is wrong

- Uniform `p-3 / gap-3` everywhere means the dense rail and the airy dashboard
  get identical rhythm. Dashboard should breathe more, rail should be tighter.
- Readout uses `p-3` inside a `gap-3` stack inside `p-3` page → triple padding
  pile-up on the most important element.
- Heatmap `minHeight:220` but cells `min-h-[70px]` + wrap → frequent awkward empty
  band at the bottom.

## 5. Which borders are too harsh

- `border-border (#1e2630)` on all panels, table row dividers (`border-border/50`),
  the nav header, the tape cells, metric tiles. All of it should drop to a ~6%
  hairline; structural separation should come from panel fill + spacing.

## 6. Which colors are too loud

- Accent blue `#2f81f7` (overused). Up `#16c784` / down `#ea3943` (neon).
- Readout `bg-accent/5` tint. Active timeframe `bg-accent text-white` (pure white
  on saturated blue = harsh).

## 7. Which typography is weak

- No tabular alignment discipline outside `.num`. Inter without feature settings.
- Giant nothing: page `h1` is `text-lg` while the ticker price is `text-2xl` —
  inconsistent emphasis. Labels and values not differentiated enough in weight.

## 8. Which panels should be merged or simplified

- Rail has **4 separate bordered cards** (Portfolio / Movers / Research / Data
  status). Should read as one continuous rail with hairline separators, not four
  caged boxes.
- Dashboard "Missing data" + "What to check next" + "Biggest risks" are three
  boxes saying related things; tighten visually.

## 9. Which charts need visual polish

- `MarketPriceChart`: grid `#1a212b` lines visible, transparent bg is fine but the
  surrounding panel border fights the chart's own price-scale border (double
  line). Header price `text-2xl` next to a `text-lg` symbol is unbalanced.
  Crosshair/series colors are the neon greens.

## 10. Which pages need layout simplification

- `/market`: too many equal boxes; chart must dominate, everything else recede.
- `/dashboard`: should be calmer/centered (it is `max-w-5xl`) but still wrapped in
  hard boxes; needs whitespace + fewer borders.
- `/risk`: four `RiskCard`s with colored dots but no real severity language;
  wants low/med/high chips and a collapsed raw-warnings section.
- `/ticker`: metric tiles + score table are boxy; N/A handling is honest but
  visually noisy.

## Direction for the rebuild

1. **Elevation, not cages.** Darken the app bg, lift panels, drop borders to
   hairlines. Separation = fill + space.
2. **Calm semantic palette.** Desaturate up/down, mute the gold, restrain the
   blue to interactive/active only, add a sparing teal.
3. **Type rhythm.** Inter with feature settings for UI, mono tabular for all
   numbers, a small disciplined scale (label / body / value / headline).
4. **Hierarchy.** One primary object per screen (chart on /market, readout on
   /dashboard); supporting modules recede.
5. **Quiet interaction.** Hover = subtle fill; active = thin precise accent.

## Rebuild outcome (what shipped)

**Tokens** (`tailwind.config.ts`, `globals.css`): kept token *names* so every page
inherited the change. New values — bg `#0a0c10`, panel ramp `#11151c / #171c25 /
#1e242f`, hairline border `#1b212b`, soft-white text `#e6e9ef`, calm semantics
(up `#3fb950`, down `#e5534b`, warn `#d6a121`, accent `#4c8dff`, teal `#2bb6a3`).
Added Inter feature-settings, `.label`/`.num` refinements, `.accent-stripe`,
selection color, shadow ramp, refined scrollbars/radii.

**Primitives rewritten:** `Panel` (hairline + elevation + optional accent stripe,
no hard cage), `MetricTile`, `MarketTopStrip` (thin single-row tape), `Badges`
(dot+text, thin) + new `SeverityChip` (low/med/high), `TimeframeSelector` /
`ChartTypeToggle` / `ModeToggle` (quiet segmented controls), `HBarList`
(rounded slim bars), `MarketHeatmap` (rounded cells, gap-1, calmer ramp),
`MarketPriceChart` (new palette, faint grid), `TerminalShell` (underline active
nav), `TodaysReadout` (calm panel + accent stripe, dropped the blue wash),
`PortfolioTable` (sticky header, hairline rows, tabular alignment), `Contributors`.

**Pages:** `/market` (chart is the elevated primary module), `/dashboard` (calmer
rhythm, `space-y-5`), `/portfolio`, `/ticker` (thesis stripe + scores as meter
rows, not a table), `/risk` (diagnosis stripe + severity chips + raw warnings
collapsed into `<details>`), `/coverage`, `/system` headers refreshed.

**Deleted (visual junk / orphans):** `ResearchDashboardClient`, `PortfolioLiveTable`,
`LivePriceChart`, `PriceChart`, `Sidebar`, `ThemePieChart`, `HoldingsBarChart`,
`ThemeBarChart`, `TooltipHint`. `/live` chain (`LiveMonitorClient`,
`LiveMarketStrip`, `StreamDebugPanel`) left intact — fold in later.

**Verification:** `npm run build` clean; backend `pytest` 230 passed;
`tests/m8_10.spec.ts` 6 passed (market/chart, dashboard readout, portfolio
total, ticker PLTR, risk severity, coverage+system) with no key leak, no buy/sell,
no invalid date. Screenshots `screenshots/m8_10_*.png` inspected by eye.

**Remaining weaknesses:** slim HBar fills read subtle at full-page zoom (by design,
calm); `/live` still off-theme; rail is four refined panels rather than one merged
rail; no light mode.
