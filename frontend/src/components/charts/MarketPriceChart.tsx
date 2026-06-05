'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { getApiBase } from '@/lib/api'
import { isNum, money, pct, timeAgo } from '@/lib/format'
import { ChartTypeToggle, TF_TO_RANGE, TIMEFRAMES, TimeframeSelector, type Timeframe } from '@/components/ui/TimeframeSelector'
import { ChartLoading, EmptyState } from '@/components/ui/States'

type Candle = { t: number; o?: number; h?: number; l?: number; c: number }
type Quote = { c?: number; d?: number; dp?: number; t?: number; provider_used?: string; delayed?: boolean }

const C = {
  up: '#3fb950',
  down: '#e5534b',
  line: '#4c8dff',
  grid: 'rgba(255,255,255,0.035)',
  text: '#5b6573',
  border: 'rgba(255,255,255,0.06)',
}

export function MarketPriceChart({
  ticker,
  height = 440,
  defaultTimeframe = '1M',
  showHeader = true,
}: {
  ticker: string
  height?: number
  defaultTimeframe?: Timeframe
  showHeader?: boolean
}) {
  const symbol = ticker.toUpperCase()
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | ISeriesApi<'Candlestick'> | null>(null)

  const [tf, setTf] = useState<Timeframe>(defaultTimeframe)
  const [type, setType] = useState<'line' | 'candles'>('line')
  const [data, setData] = useState<Candle[]>([])
  const [quote, setQuote] = useState<Quote | null>(null)
  const [loading, setLoading] = useState(true)
  const [emptyReason, setEmptyReason] = useState<string | null>(null)
  const [hover, setHover] = useState<{ price: number } | null>(null)

  // fetch history on ticker/timeframe change
  useEffect(() => {
    let alive = true
    setLoading(true)
    setEmptyReason(null)
    const range = TF_TO_RANGE[tf]
    fetch(`${getApiBase()}/api/market/history/${symbol}?range=${range}`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (!alive) return
        const hist: Candle[] = (j?.history || []).filter((d: Candle) => isNum(d.t) && isNum(d.c))
        setData(hist)
        if (hist.length === 0) {
          setEmptyReason(
            ['1D', '5D'].includes(tf)
              ? 'intraday history unavailable with the current provider'
              : 'market history API returned no rows for this range',
          )
        }
      })
      .catch(() => alive && setEmptyReason('could not reach market history API'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [symbol, tf])

  // quote header (poll while market likely open)
  useEffect(() => {
    let alive = true
    const load = () =>
      fetch(`${getApiBase()}/api/market/quote/${symbol}`, { cache: 'no-store' })
        .then((r) => (r.ok ? r.json() : null))
        .then((q) => alive && q && !q.error && setQuote(q))
        .catch(() => {})
    load()
    const id = setInterval(load, 30_000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [symbol])

  const hasOHLC = useMemo(() => data.length > 0 && data.every((d) => isNum(d.o) && isNum(d.h) && isNum(d.l)), [data])

  // build / rebuild chart
  useEffect(() => {
    if (loading || !containerRef.current || data.length === 0) return
    const el = containerRef.current
    const width = el.clientWidth
    if (width <= 0) return

    const chart = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: C.text, fontSize: 11 },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      width,
      height,
      rightPriceScale: { borderColor: C.border },
      timeScale: { borderColor: C.border, timeVisible: ['1D', '5D'].includes(tf), secondsVisible: false },
      crosshair: { mode: 1 },
    })
    chartRef.current = chart

    const useCandles = type === 'candles' && hasOHLC
    if (useCandles) {
      const s = chart.addCandlestickSeries({
        upColor: C.up, downColor: C.down, borderUpColor: C.up, borderDownColor: C.down,
        wickUpColor: C.up, wickDownColor: C.down,
      })
      s.setData(
        data.map((d) => ({ time: d.t as UTCTimestamp, open: d.o!, high: d.h!, low: d.l!, close: d.c })),
      )
      seriesRef.current = s
    } else {
      const first = data[0].c
      const last = data[data.length - 1].c
      const lineColor = last >= first ? C.up : C.down
      const s = chart.addLineSeries({ color: lineColor, lineWidth: 2, crosshairMarkerRadius: 3 })
      s.setData(data.map((d) => ({ time: d.t as UTCTimestamp, value: d.c })))
      seriesRef.current = s
    }
    chart.timeScale().fitContent()

    chart.subscribeCrosshairMove((p) => {
      if (!p.point || !seriesRef.current || !p.seriesData) {
        setHover(null)
        return
      }
      const sd = p.seriesData.get(seriesRef.current) as { value?: number; close?: number } | undefined
      const v = sd?.value ?? sd?.close
      setHover(isNum(v) ? { price: v! } : null)
    })

    const ro = new ResizeObserver(() => {
      const w = el.clientWidth
      if (w > 0) chart.applyOptions({ width: w })
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [data, loading, type, hasOHLC, height, tf])

  const price = hover?.price ?? quote?.c ?? (data.length ? data[data.length - 1].c : undefined)
  const dir = isNum(quote?.dp) ? (quote!.dp! >= 0 ? 'up' : 'down') : 'flat'
  const priceColor = dir === 'up' ? 'text-up' : dir === 'down' ? 'text-down' : 'text-foreground'

  return (
    <div className="flex h-full flex-col">
      {showHeader && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.05] px-3 py-2.5">
          <div className="flex items-baseline gap-3">
            <span className="text-base font-bold tracking-wide">{symbol}</span>
            <span className={`num text-xl font-semibold tracking-tight ${priceColor}`}>
              {isNum(price) ? money(price) : '—'}
            </span>
            {isNum(quote?.d) && (
              <span className={`num text-xs font-medium ${priceColor}`}>
                {quote!.d! >= 0 ? '▲' : '▼'} {money(Math.abs(quote!.d!))} ({pct(quote?.dp, { signed: true })})
              </span>
            )}
            <span className="text-2xs text-faint">
              {quote?.provider_used ? `${quote.provider_used}${quote.delayed ? ' · delayed' : ''}` : 'no live quote'}
              {isNum(quote?.t) ? ` · ${timeAgo(quote!.t)}` : ''}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ChartTypeToggle value={type} onChange={setType} />
            <TimeframeSelector value={tf} onChange={setTf} options={TIMEFRAMES as unknown as Timeframe[]} />
          </div>
        </div>
      )}
      <div className="relative flex-1">
        {loading ? (
          <ChartLoading height={height} />
        ) : data.length === 0 ? (
          <div style={{ height }} className="flex items-center justify-center">
            <EmptyState title={`No chart data for ${symbol}`} hint={emptyReason ?? undefined} icon="📉" />
          </div>
        ) : (
          <div ref={containerRef} data-testid="price-chart" className="w-full" style={{ height }} />
        )}
        {type === 'candles' && !hasOHLC && data.length > 0 && (
          <div className="absolute left-3 top-2 text-2xs text-warn">
            candles need OHLC — provider returned close-only, showing line
          </div>
        )}
      </div>
    </div>
  )
}
