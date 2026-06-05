'use client'

import { useEffect, useSyncExternalStore } from 'react'
import { getLiveQuoteStore, type StreamMode } from '@/lib/liveQuotes'

export function useLiveQuotes(tickers: string[]) {
  const tickerKey = tickers.join(',')

  const state = useSyncExternalStore(
    (cb) => getLiveQuoteStore().subscribe(cb),
    () => getLiveQuoteStore().getSnapshot(),
    () => getLiveQuoteStore().getSnapshot(),
  )

  useEffect(() => {
    getLiveQuoteStore().connect(tickers)
    return () => getLiveQuoteStore().disconnect()
  }, [tickerKey])

  const getPrice = (ticker: string) => state.quotes.get(ticker.toUpperCase())

  return { ...state, getPrice }
}

export function streamModeLabel(mode: StreamMode, debug?: { provider?: string; marketOpen?: boolean }): string {
  if (mode === 'live') return 'Live: Finnhub WebSocket'
  if (mode === 'market_closed') return 'Market closed — Finnhub connected'
  if (mode === 'polling') {
    if (debug?.provider === 'finnhub_ws') return 'Finnhub reconnecting…'
    return 'Polling fallback (not real-time)'
  }
  return 'Offline'
}

export function streamModeColor(mode: StreamMode): string {
  switch (mode) {
    case 'live':
      return 'bg-green-500/10 border-green-500/30 text-green-400'
    case 'polling':
      return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
    case 'market_closed':
      return 'bg-blue-500/10 border-blue-500/30 text-blue-400'
    default:
      return 'bg-red-500/10 border-red-500/30 text-red-400'
  }
}
