'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getApiBase } from '@/lib/api'
import { isNum, money, pct } from '@/lib/format'

// Label -> proxy symbol. Indices aren't on finnhub free, so we use liquid ETF /
// futures proxies and fall back to yfinance server-side. Honest labelling: these
// are proxies, shown as such.
const TAPE: { label: string; symbol: string }[] = [
  { label: 'S&P 500', symbol: 'SPY' },
  { label: 'Nasdaq 100', symbol: 'QQQ' },
  { label: 'Dow', symbol: 'DIA' },
  { label: 'Russell 2000', symbol: 'IWM' },
  { label: 'VIX', symbol: '^VIX' },
  { label: 'Gold', symbol: 'GLD' },
  { label: 'Bitcoin', symbol: 'BTC-USD' },
  { label: 'Brent', symbol: 'BZ=F' },
]

type Q = { c?: number; dp?: number; error?: string }

export function MarketTopStrip() {
  const [quotes, setQuotes] = useState<Record<string, Q>>({})

  useEffect(() => {
    let alive = true
    const load = async () => {
      const entries = await Promise.all(
        TAPE.map(async ({ symbol }) => {
          try {
            const r = await fetch(`${getApiBase()}/api/market/quote/${encodeURIComponent(symbol)}`, { cache: 'no-store' })
            return [symbol, r.ok ? await r.json() : { error: 'fetch' }] as const
          } catch {
            return [symbol, { error: 'fetch' }] as const
          }
        }),
      )
      if (alive) setQuotes(Object.fromEntries(entries))
    }
    load()
    const id = setInterval(load, 60_000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return (
    <div className="flex items-stretch overflow-x-auto border-b border-white/[0.05] bg-background">
      {TAPE.map(({ label, symbol }) => {
        const q = quotes[symbol]
        const has = q && !q.error && isNum(q.c)
        const dp = q?.dp
        const up = isNum(dp) && dp! >= 0
        const color = !isNum(dp) ? 'text-mutedForeground' : up ? 'text-up' : 'text-down'
        return (
          <Link
            key={symbol}
            href={`/ticker/${encodeURIComponent(symbol)}`}
            className="group flex h-7 shrink-0 items-center gap-2 whitespace-nowrap border-r border-white/[0.04] px-3 transition-colors hover:bg-panel2"
            title={`proxy: ${symbol}`}
          >
            <span className="text-2xs font-medium uppercase tracking-label text-mutedForeground group-hover:text-foreground">
              {label}
            </span>
            {has ? (
              <span className="num flex items-baseline gap-1.5">
                <span className="text-2xs font-semibold text-foreground">{money(q!.c)}</span>
                <span className={`text-2xs ${color}`}>
                  {isNum(dp) ? `${up ? '▲' : '▼'} ${pct(Math.abs(dp!), { signed: false })}` : ''}
                </span>
              </span>
            ) : (
              <span className="text-2xs text-faint">—</span>
            )}
          </Link>
        )
      })}
    </div>
  )
}
