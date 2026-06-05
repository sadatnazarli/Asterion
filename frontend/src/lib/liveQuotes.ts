'use client'

type Listener = () => void

const noopStore = {
  subscribe: (_: Listener) => () => {},
  getSnapshot: () => ({
    quotes: new Map<string, QuoteTick>(),
    mode: 'offline' as StreamMode,
    debug: {
      wsConnected: false,
      provider: 'none',
      status: 'disconnected',
      message: 'SSR',
      subscribedTickers: [] as string[],
      lastTickAt: null as string | null,
      tickCount: 0,
      marketOpen: true,
    },
    stale: true,
  }),
  connect: (_: string[]) => {},
  disconnect: () => {},
  getQuote: (_: string) => undefined,
}

let clientStore: LiveQuoteStore | null = null

export type QuoteTick = {
  ticker: string
  price: number
  change_pct?: number
  timestamp: string
  provider: string
  is_realtime: boolean
}

export type StreamMode = 'live' | 'polling' | 'offline' | 'market_closed'

export type StreamStatus = {
  status: string
  provider: string
  message: string
  market_open?: boolean
}

export type LiveQuoteDebug = {
  wsConnected: boolean
  provider: string
  status: string
  message: string
  subscribedTickers: string[]
  lastTickAt: string | null
  tickCount: number
  marketOpen: boolean
}

import { getApiBase, getWsBase } from '@/lib/api'

type ListenerFn = () => void

class LiveQuoteStore {
  private ws: WebSocket | null = null
  private quotes = new Map<string, QuoteTick>()
  private listeners = new Set<ListenerFn>()
  private tickCount = 0
  private lastTickAt: string | null = null
  private streamStatus: StreamStatus = {
    status: 'disconnected',
    provider: 'none',
    message: 'Not connected',
  }
  private subscribedTickers: string[] = []
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private staleTimer: ReturnType<typeof setInterval> | null = null
  private refCount = 0
  private cachedSnapshot: {
    quotes: Map<string, QuoteTick>
    mode: StreamMode
    debug: LiveQuoteDebug
    stale: boolean
  } | null = null

  subscribe(listener: ListenerFn): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notify() {
    this.cachedSnapshot = null
    this.listeners.forEach((l) => l())
  }

  getSnapshot() {
    if (!this.cachedSnapshot) {
      this.cachedSnapshot = {
        quotes: this.quotes,
        mode: this.getMode(),
        debug: this.getDebug(),
        stale: this.isStale(),
      }
    }
    return this.cachedSnapshot
  }

  getQuote(ticker: string): QuoteTick | undefined {
    return this.quotes.get(ticker.toUpperCase())
  }

  getAllQuotes(): Map<string, QuoteTick> {
    return this.quotes
  }

  getMode(): StreamMode {
    const s = this.streamStatus.status
    if (s === 'connected' && this.streamStatus.market_open === false) return 'market_closed'
    if (s === 'connected' || s === 'connecting') return 'live'
    if (s === 'fallback') return 'polling'
    return 'offline'
  }

  isStale(): boolean {
    if (!this.lastTickAt) return true
    return Date.now() - new Date(this.lastTickAt).getTime() > 60_000
  }

  getDebug(): LiveQuoteDebug {
    return {
      wsConnected: this.ws?.readyState === WebSocket.OPEN,
      provider: this.streamStatus.provider,
      status: this.streamStatus.status,
      message: this.streamStatus.message,
      subscribedTickers: [...this.subscribedTickers],
      lastTickAt: this.lastTickAt,
      tickCount: this.tickCount,
      marketOpen: this.streamStatus.market_open ?? false,
    }
  }

  connect(tickers: string[]) {
    this.refCount += 1
    const normalized = [...new Set(tickers.map((t) => t.toUpperCase()).filter(Boolean))]
    if (normalized.join(',') === this.subscribedTickers.join(',') && this.ws?.readyState === WebSocket.OPEN) {
      return
    }
    this.subscribedTickers = normalized
    this.openSocket()
    if (!this.staleTimer) {
      this.staleTimer = setInterval(() => this.notify(), 5000)
    }
  }

  disconnect() {
    this.refCount = Math.max(0, this.refCount - 1)
    if (this.refCount > 0) return
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.staleTimer) {
      clearInterval(this.staleTimer)
      this.staleTimer = null
    }
    this.ws?.close()
    this.ws = null
  }

  private openSocket() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    if (!this.subscribedTickers.length) return

    const url = `${getWsBase()}/ws/quotes?tickers=${this.subscribedTickers.join(',')}`
    const ws = new WebSocket(url)
    this.ws = ws

    ws.onopen = () => {
      this.streamStatus = { ...this.streamStatus, status: 'connecting', message: 'WebSocket open' }
      this.notify()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'quote_tick') {
          const tick: QuoteTick = {
            ticker: data.ticker,
            price: data.price,
            change_pct: data.change_pct,
            timestamp: data.timestamp,
            provider: data.provider,
            is_realtime: data.is_realtime,
          }
          this.quotes.set(tick.ticker, tick)
          this.tickCount += 1
          this.lastTickAt = tick.timestamp
        } else if (data.type === 'stream_status') {
          this.streamStatus = {
            status: data.status,
            provider: data.provider,
            message: data.message || '',
            market_open: data.market_open,
          }
        }
        this.notify()
      } catch {
        /* ignore */
      }
    }

    ws.onclose = () => {
      this.streamStatus = {
        status: 'disconnected',
        provider: this.streamStatus.provider,
        message: 'WebSocket closed — reconnecting',
      }
      this.notify()
      if (this.refCount > 0) {
        this.reconnectTimer = setTimeout(() => this.openSocket(), 3000)
      }
    }

    ws.onerror = () => {
      this.streamStatus = {
        status: 'disconnected',
        provider: this.streamStatus.provider,
        message: 'WebSocket error',
      }
      this.notify()
    }
  }
}

export function getLiveQuoteStore(): LiveQuoteStore | typeof noopStore {
  if (typeof window === 'undefined') return noopStore
  if (!clientStore) clientStore = new LiveQuoteStore()
  return clientStore
}
