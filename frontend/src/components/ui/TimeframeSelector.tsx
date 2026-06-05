'use client'

export const TIMEFRAMES = ['1D', '5D', '1M', '6M', 'YTD', '1Y', '5Y', 'ALL'] as const
export type Timeframe = (typeof TIMEFRAMES)[number]

// maps UI timeframe -> backend ?range= value
export const TF_TO_RANGE: Record<Timeframe, string> = {
  '1D': '1d',
  '5D': '5d',
  '1M': '1m',
  '6M': '6m',
  YTD: 'ytd',
  '1Y': '1y',
  '5Y': '5y',
  ALL: 'max',
}

export function TimeframeSelector({
  value,
  onChange,
  options = TIMEFRAMES as unknown as Timeframe[],
}: {
  value: Timeframe
  onChange: (tf: Timeframe) => void
  options?: Timeframe[]
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-md border border-white/[0.06] bg-panel2 p-0.5">
      {options.map((tf) => (
        <button
          key={tf}
          type="button"
          onClick={() => onChange(tf)}
          className={`rounded px-2 py-0.5 text-2xs font-semibold tabular-nums transition-colors ${
            value === tf
              ? 'bg-panel3 text-accent shadow-sm'
              : 'text-mutedForeground hover:text-foreground'
          }`}
        >
          {tf}
        </button>
      ))}
    </div>
  )
}

export function ChartTypeToggle({
  value,
  onChange,
}: {
  value: 'line' | 'candles'
  onChange: (v: 'line' | 'candles') => void
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-md border border-white/[0.06] bg-panel2 p-0.5">
      {(['line', 'candles'] as const).map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => onChange(t)}
          className={`rounded px-2 py-0.5 text-2xs font-semibold capitalize transition-colors ${
            value === t ? 'bg-panel3 text-foreground shadow-sm' : 'text-mutedForeground hover:text-foreground'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}
