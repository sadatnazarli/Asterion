'use client'

import { streamModeLabel, useLiveQuotes } from '@/hooks/useLiveQuotes'

const DEFAULT_TICKERS = ['MSFT', 'NVDA', 'META', 'PLTR', 'VOO', 'VRT']

export default function StreamDebugPanel({ tickers = DEFAULT_TICKERS }: { tickers?: string[] }) {
  const { debug, mode, quotes } = useLiveQuotes(tickers)

  return (
    <div
      data-testid="stream-debug-panel"
      className="rounded-xl border border-dashed border-border bg-muted/10 p-4 text-xs font-mono space-y-2"
    >
      <div className="font-semibold text-sm font-sans">Stream debug (dev)</div>
      <div>WebSocket: {debug.wsConnected ? 'connected' : 'disconnected'}</div>
      <div>Mode: {streamModeLabel(mode, debug)}</div>
      <div>Provider: {debug.provider}</div>
      <div>Status: {debug.status}</div>
      <div>Message: {debug.message || '—'}</div>
      <div>Subscribed: {debug.subscribedTickers.join(', ') || '—'}</div>
      <div>Last tick: {debug.lastTickAt || 'none'}</div>
      <div>Ticks received: {debug.tickCount}</div>
      <div>Market open: {debug.marketOpen ? 'yes' : 'no'}</div>
      <div className="pt-1 border-t border-border">
        Latest prices:{' '}
        {Array.from(quotes.entries())
          .map(([t, q]) => `${t}=$${q.price.toFixed(2)}`)
          .join(' · ') || 'waiting…'}
      </div>
    </div>
  )
}
