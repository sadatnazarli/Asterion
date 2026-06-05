'use client'

import Link from 'next/link'
import { isNum, pct } from '@/lib/format'

export type HeatCell = {
  ticker: string
  value: number // size weight (portfolio value or mkt cap)
  daily_change_pct?: number | null
}

// Color by daily %, area by value. Not a true squarified treemap — a weighted
// mosaic (flex-basis ∝ value) which reads like the Yahoo heatmap and stays
// robust at any aspect ratio.
function cellColor(dp?: number | null): string {
  if (!isNum(dp)) return 'rgba(91,101,115,0.12)'
  const clamped = Math.max(-3, Math.min(3, dp)) / 3 // -1..1
  if (clamped >= 0) {
    const a = 0.1 + clamped * 0.34 // calmer ceiling than crypto-neon
    return `rgba(63,185,80,${a.toFixed(3)})`
  }
  const a = 0.1 + Math.abs(clamped) * 0.34
  return `rgba(229,83,75,${a.toFixed(3)})`
}

export function MarketHeatmap({ cells }: { cells: HeatCell[] }) {
  const total = cells.reduce((s, c) => s + (isNum(c.value) ? c.value : 0), 0) || 1
  const sorted = [...cells].filter((c) => isNum(c.value) && c.value > 0).sort((a, b) => b.value - a.value)

  if (sorted.length === 0) {
    return <div className="px-3 py-6 text-center text-2xs text-faint">no holdings to map</div>
  }

  return (
    <div className="flex flex-wrap gap-1" style={{ minHeight: 210 }}>
      {sorted.map((c) => {
        const wPct = (c.value / total) * 100
        const up = isNum(c.daily_change_pct) && c.daily_change_pct! >= 0
        return (
          <Link
            key={c.ticker}
            href={`/ticker/${encodeURIComponent(c.ticker)}`}
            className="group relative flex min-h-[64px] flex-1 flex-col justify-center overflow-hidden rounded-md border border-white/[0.04] px-2.5 py-2 ring-inset transition-all hover:ring-1 hover:ring-white/15"
            style={{
              flexGrow: c.value,
              flexBasis: `${Math.max(13, wPct)}%`,
              backgroundColor: cellColor(c.daily_change_pct),
            }}
            title={`${c.ticker} · ${isNum(c.daily_change_pct) ? pct(c.daily_change_pct, { signed: true }) : 'n/a'}`}
          >
            <span className="num text-sm font-bold tracking-tight text-foreground">{c.ticker}</span>
            <span className={`num text-2xs font-medium ${up ? 'text-up' : 'text-down'}`}>
              {isNum(c.daily_change_pct) ? pct(c.daily_change_pct, { signed: true }) : '—'}
            </span>
          </Link>
        )
      })}
    </div>
  )
}
