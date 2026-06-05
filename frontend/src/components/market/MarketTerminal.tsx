'use client'

import { useState } from 'react'
import Link from 'next/link'
import { MarketPriceChart } from '@/components/charts/MarketPriceChart'
import { MarketHeatmap, type HeatCell } from '@/components/market/MarketHeatmap'
import { Panel } from '@/components/ui/Panel'
import { ModeGate, BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { HelpTip } from '@/components/ui/HelpTip'
import { define } from '@/lib/glossary'
import { LiveModeBadge, type LiveMode } from '@/components/ui/Badges'
import { ContributorColumns } from '@/components/portfolio/Contributors'
import { TodaysReadout } from '@/components/portfolio/TodaysReadout'
import { type Contributors } from '@/lib/insights'
import { compactMoney, isNum, money, pct, timeAgo } from '@/lib/format'

type Holding = { ticker: string; current_value: number; daily_change_pct?: number | null; weight?: number }
type Report = { name: string; type: string }
type ProviderInfo = { configured: boolean; status: string }

const REFERENCE = new Set(['SPY', 'VOO', 'QQQ', 'DIA', 'IWM', 'IVV'])

export function MarketTerminal({
  holdings,
  totalValue,
  dailyPnl,
  dailyPnlPct,
  reports,
  providers,
  contributors,
  mainRisk,
  nextAction,
  liveMode,
  providerName,
  lastUpdated,
  researchItems,
}: {
  holdings: Holding[]
  totalValue: number
  dailyPnl: number
  dailyPnlPct: number
  reports: Report[]
  providers: Record<string, ProviderInfo> | null
  contributors: Contributors
  mainRisk: string
  nextAction: string
  liveMode: LiveMode
  providerName: string
  lastUpdated: string | null
  researchItems: { text: string; href: string }[]
}) {
  const byValue = [...holdings].sort((a, b) => b.current_value - a.current_value)
  const watchlist = Array.from(new Set(['SPY', 'QQQ', ...byValue.slice(0, 6).map((h) => h.ticker)]))
  const [ticker, setTicker] = useState(watchlist[0] ?? 'SPY')
  const [input, setInput] = useState('')

  const isReference = REFERENCE.has(ticker.toUpperCase())
  const heatCells: HeatCell[] = holdings.map((h) => ({ ticker: h.ticker, value: h.current_value, daily_change_pct: h.daily_change_pct }))

  // drag / support tickers from contribution ranking
  const drag = contributors.all.filter((r) => r.estimated_contribution_dollars < 0).slice(-4).reverse().map((r) => r.ticker)
  const support = contributors.all.filter((r) => r.estimated_contribution_dollars > 0).slice(0, 4).map((r) => r.ticker)

  const pnlColor = dailyPnl >= 0 ? 'text-up' : 'text-down'

  return (
    <div className="grid grid-cols-1 gap-3 p-3 xl:grid-cols-[1fr_320px]">
      {/* main column */}
      <div className="space-y-3">
        <BeginnerOnly>
          <HelpBox answers="Is the whole market moving, or only my holdings?">
            Compare a market reference (SPY/VOO) against your own holdings. If both fall together, it’s a market day, not a you problem.
          </HelpBox>
        </BeginnerOnly>

        <TodaysReadout
          totalValue={totalValue}
          dailyPnl={dailyPnl}
          dailyPnlPct={dailyPnlPct}
          contributors={contributors}
          mainRisk={mainRisk}
          nextAction={nextAction}
        />

        {/* ticker selector + purpose label */}
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (input.trim()) setTicker(input.trim().toUpperCase())
                setInput('')
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Search ticker…"
                className="num h-7 w-32 rounded border border-white/[0.07] bg-panel2 px-2.5 text-xs text-foreground placeholder:text-faint focus:border-accent/60 focus:outline-none"
              />
            </form>
            {watchlist.map((t) => (
              <button
                key={t}
                onClick={() => setTicker(t)}
                className={`num rounded border px-2 py-1 text-2xs font-semibold transition-colors ${
                  ticker === t
                    ? 'border-accent/50 bg-accent/10 text-accent'
                    : 'border-white/[0.06] text-mutedForeground hover:border-white/15 hover:text-foreground'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <p className="text-2xs text-faint">
            <span
              className={`mr-1.5 rounded border bg-white/[0.02] px-1.5 py-0.5 font-semibold uppercase tracking-label ${
                isReference ? 'border-accent/30 text-accent' : 'border-warn/30 text-warn'
              }`}
            >
              {isReference ? 'Market reference' : 'Portfolio holding'}
            </span>
            {isReference
              ? `${ticker} is the broad-market reference. Switch to a holding (e.g. MSFT, NVDA) to inspect your own exposure.`
              : `${ticker} is one of your holdings. Switch to SPY/VOO for the broad-market reference.`}
          </p>
        </div>

        {/* big chart — the primary module on this screen */}
        <div className="overflow-hidden rounded-md border border-white/[0.07] bg-panel shadow-elev">
          <MarketPriceChart ticker={ticker} height={460} defaultTimeframe="6M" />
        </div>

        {/* heatmap with explanation (terminal density) */}
        <ModeGate mode="terminal">
          <Panel title="Portfolio heatmap">
            <p className="mb-2 text-2xs text-mutedForeground">Size = position value · color = today&apos;s % move.</p>
            <MarketHeatmap cells={heatCells} />
            <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-2xs">
              <span><span className="text-down">Today&apos;s drag:</span> <span className="num">{drag.join(', ') || '—'}</span></span>
              <span><span className="text-up">Today&apos;s support:</span> <span className="num">{support.join(', ') || '—'}</span></span>
            </div>
          </Panel>
        </ModeGate>
      </div>

      {/* right intelligence rail */}
      <aside className="space-y-3">
        {/* 1. Portfolio */}
        <Panel title="Portfolio">
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <span className="text-2xs text-mutedForeground">Total value</span>
              <span className="num text-lg font-bold">{money(totalValue)}</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-2xs text-mutedForeground">Today</span>
              <span className={`num text-sm font-semibold ${pnlColor}`}>
                {dailyPnl >= 0 ? '+' : ''}
                {money(dailyPnl).replace('$-', '-$')} ({pct(dailyPnlPct, { signed: true })})
              </span>
            </div>
            <Link href="/dashboard" className="block pt-1 text-2xs text-accent hover:underline">
              Open portfolio intelligence →
            </Link>
          </div>
        </Panel>

        {/* 2. Today's movers */}
        <Panel title="Today's movers">
          <ContributorColumns positive={contributors.top_positive} negative={contributors.top_negative} />
        </Panel>

        {/* 3. Research queue */}
        <Panel title="Research queue">
          <ul className="mb-2 space-y-1">
            {researchItems.length === 0 ? (
              <li className="text-2xs text-up">No outstanding research items.</li>
            ) : (
              researchItems.map((r, i) => (
                <li key={i}>
                  <Link href={r.href} className="flex gap-1.5 text-2xs text-mutedForeground hover:text-foreground">
                    <span className="text-accent">→</span>
                    {r.text}
                  </Link>
                </li>
              ))
            )}
          </ul>
          <div className="border-t border-border pt-2">
            <div className="mb-1 text-2xs uppercase tracking-wider text-faint">Latest reports</div>
            {reports.slice(0, 3).map((r) => (
              <Link
                key={r.name}
                href={`/reports/${encodeURIComponent(r.name)}`}
                className="block truncate rounded px-1 py-0.5 text-2xs text-mutedForeground hover:bg-panel2 hover:text-foreground"
              >
                {r.name}
              </Link>
            ))}
            {reports.length > 3 && (
              <Link href="/reports" className="mt-0.5 block px-1 text-2xs text-accent hover:underline">
                view all ({reports.length}) →
              </Link>
            )}
          </div>
        </Panel>

        {/* 4. Data status */}
        <Panel title="Data status">
          <div className="space-y-1.5">
            <LiveModeBadge mode={liveMode} provider={providerName} />
            <div className="flex items-center justify-between text-2xs">
              <span className="flex items-center gap-1 text-mutedForeground">
                Quote provider
                <HelpTip text={define('live provider') ?? ''} label="live provider" />
              </span>
              <span className="num capitalize">{providerName}</span>
            </div>
            <div className="flex items-center justify-between text-2xs">
              <span className="text-mutedForeground">Last updated</span>
              <span className="num">{lastUpdated ? timeAgo(lastUpdated) : '—'}</span>
            </div>
            <ModeGate mode="terminal">
              <div className="border-t border-border pt-1.5">
                {providers &&
                  Object.entries(providers)
                    .filter(([k]) => ['finnhub', 'yfinance', 'fmp', 'fred', 'polygon'].includes(k))
                    .map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between text-2xs">
                        <span className="capitalize text-mutedForeground">{k}</span>
                        <span className={v.configured || v.status === 'fallback' ? 'text-up' : 'text-faint'}>{v.status}</span>
                      </div>
                    ))}
                <Link href="/system" className="block pt-1 text-2xs text-accent hover:underline">Provider details →</Link>
              </div>
            </ModeGate>
          </div>
        </Panel>
      </aside>
    </div>
  )
}
