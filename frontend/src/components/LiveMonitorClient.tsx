'use client'

import LiveMarketStrip from '@/components/LiveMarketStrip'
import StreamDebugPanel from '@/components/StreamDebugPanel'
import { streamModeColor, streamModeLabel, useLiveQuotes } from '@/hooks/useLiveQuotes'

const MONITOR_TICKERS = ['MSFT', 'NVDA', 'META', 'PLTR', 'VOO', 'VRT']

export default function LiveMonitorClient({
  initialQuotes,
  finnhubConfigured,
  setupHint,
}: {
  initialQuotes: Record<string, { price: number; change_pct: number }>
  finnhubConfigured: boolean
  setupHint?: string
}) {
  const { mode, debug } = useLiveQuotes(MONITOR_TICKERS)

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-10">
      <div className="flex justify-between items-end border-b border-border pb-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Live Market Monitor</h2>
          <p className="text-muted-foreground mt-1">
            Watch prices move in real time — separate from the research dashboard
          </p>
        </div>
        <span
          data-testid="live-status-badge"
          className={`text-xs px-2 py-1 rounded border ${streamModeColor(mode)}`}
        >
          {streamModeLabel(mode, debug)}
        </span>
      </div>

      {!finnhubConfigured && (
        <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-200">
          Finnhub is not configured. The stream uses polling every ~45 seconds — this is not true real-time.
          {setupHint && <span className="block mt-1 text-yellow-400/80">{setupHint}</span>}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card p-5 text-sm text-muted-foreground">
        <p>
          This page connects to the server WebSocket at <code className="text-foreground">/ws/quotes</code>.
          The server holds your Finnhub key — it never reaches the browser.
          When the US market is open and Finnhub is configured, prices should tick within seconds.
        </p>
      </div>

      <LiveMarketStrip initialQuotes={initialQuotes} />
      <StreamDebugPanel tickers={MONITOR_TICKERS} />

      <div className="text-xs text-muted-foreground">
        Ticks received: {debug.tickCount} · Last: {debug.lastTickAt || 'none'} · Provider: {debug.provider}
      </div>
    </div>
  )
}
