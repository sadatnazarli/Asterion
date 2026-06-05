'use client'

import Link from 'next/link'
import { streamModeColor, streamModeLabel, useLiveQuotes } from '@/hooks/useLiveQuotes'

const STRIP_TICKERS = ['MSFT', 'NVDA', 'META', 'PLTR', 'VOO', 'VRT']

export default function LiveMarketStrip({
  initialQuotes,
}: {
  initialQuotes?: Record<string, { price: number; change_pct: number }>
}) {
  const { mode, stale, debug, getPrice } = useLiveQuotes(STRIP_TICKERS)

  return (
    <section className="space-y-3" data-testid="live-market-strip">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold">Live Market Strip</h3>
          <p className="text-xs text-muted-foreground">Prices update when the server receives a new tick.</p>
        </div>
        <span
          data-testid="live-status-badge"
          className={`text-xs px-2 py-1 rounded border ${streamModeColor(mode)}`}
        >
          {streamModeLabel(mode, debug)}
          {stale && mode === 'live' ? ' · stale >60s' : ''}
        </span>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1">
        {STRIP_TICKERS.map((ticker) => {
          const live = getPrice(ticker)
          const price = live?.price ?? initialQuotes?.[ticker]?.price
          const pct = live?.change_pct ?? initialQuotes?.[ticker]?.change_pct ?? 0
          const isUp = pct >= 0
          return (
            <Link
              key={ticker}
              href={`/ticker/${ticker}`}
              className="rounded-lg border border-border bg-card/80 px-4 py-3 min-w-[120px] hover:border-blue-500/40 transition-colors"
            >
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-muted-foreground">{ticker}</span>
                {live?.is_realtime && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-60" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                )}
              </div>
              <div className="text-lg font-bold tabular-nums mt-0.5">
                {price !== undefined ? `$${price.toFixed(2)}` : '—'}
              </div>
              <div className={`text-xs tabular-nums ${isUp ? 'text-green-500' : 'text-red-500'}`}>
                {isUp ? '+' : ''}{pct.toFixed(2)}% today
              </div>
            </Link>
          )
        })}
      </div>
      {debug.message && <p className="text-[11px] text-muted-foreground">{debug.message}</p>}
    </section>
  )
}
