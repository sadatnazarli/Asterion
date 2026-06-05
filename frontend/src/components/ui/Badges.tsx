import { timeAgo } from '@/lib/format'

// Data quality flag from /api/portfolio/coverage data_quality field.
export function DataQualityBadge({ quality }: { quality?: string | null }) {
  const q = (quality || 'Unknown').toLowerCase()
  const map: Record<string, { dot: string; text: string }> = {
    full: { dot: 'bg-up', text: 'text-up' },
    'full (etf)': { dot: 'bg-up', text: 'text-up' },
    partial: { dot: 'bg-warn', text: 'text-warn' },
    missing: { dot: 'bg-down', text: 'text-down' },
    unknown: { dot: 'bg-faint', text: 'text-faint' },
  }
  const m = map[q] || map.unknown
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-white/[0.07] bg-white/[0.02] px-1.5 py-0.5 text-2xs font-medium text-mutedForeground">
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      <span className={m.text}>{quality || 'Unknown'}</span>
    </span>
  )
}

// Honest live-data mode: stream / polling / stored / closed.
export type LiveMode = 'finnhub_ws' | 'polling_fallback' | 'stored' | 'closed'

export function LiveModeBadge({ mode, provider }: { mode: LiveMode; provider?: string }) {
  const map: Record<LiveMode, { label: string; text: string; dot: string }> = {
    finnhub_ws: { label: 'Live · Finnhub WS', text: 'text-up', dot: 'bg-up animate-pulse' },
    polling_fallback: { label: `Polling${provider ? ` · ${provider}` : ''}`, text: 'text-accent', dot: 'bg-accent' },
    stored: { label: 'Stored data only', text: 'text-mutedForeground', dot: 'bg-faint' },
    closed: { label: 'Market closed · last price', text: 'text-warn', dot: 'bg-warn' },
  }
  const m = map[mode]
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-white/[0.07] bg-white/[0.02] px-2 py-0.5 text-2xs font-medium">
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      <span className={m.text}>{m.label}</span>
    </span>
  )
}

// Quote provenance: which provider, cache state, last update.
export function ProviderStatusBadge({
  provider,
  lastUpdated,
  delayed,
}: {
  provider?: string | null
  lastUpdated?: string | number | null
  delayed?: boolean
}) {
  const label = provider ? provider : 'no provider'
  const color = provider === 'finnhub' ? 'text-up' : provider === 'yfinance' ? 'text-warn' : 'text-faint'
  return (
    <span className="inline-flex items-center gap-2 text-2xs text-mutedForeground">
      <span className={color}>{label}</span>
      {delayed && <span className="text-warn">delayed</span>}
      {lastUpdated != null && <span>· {timeAgo(lastUpdated)}</span>}
    </span>
  )
}

// Risk severity chip: low / medium / high — calm, single-color.
export type Severity = 'low' | 'medium' | 'high'
export function SeverityChip({ level }: { level: Severity }) {
  const map: Record<Severity, { text: string; dot: string }> = {
    low: { text: 'text-up', dot: 'bg-up' },
    medium: { text: 'text-warn', dot: 'bg-warn' },
    high: { text: 'text-down', dot: 'bg-down' },
  }
  const m = map[level]
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-white/[0.07] bg-white/[0.02] px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-label">
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      <span className={m.text}>{level}</span>
    </span>
  )
}

export function ClassificationBadge({ value }: { value?: string | null }) {
  const v = value || 'unclassified'
  const danger = /risk|watchlist|fragil|stretched|overvalued/i.test(v)
  const good = /quality|compounder|undervalued|core/i.test(v)
  const cls = danger
    ? 'border-down/30 text-down'
    : good
      ? 'border-up/30 text-up'
      : 'border-white/[0.08] text-mutedForeground'
  return (
    <span className={`inline-flex items-center rounded border bg-white/[0.02] px-2 py-0.5 text-2xs font-semibold uppercase tracking-label ${cls}`}>
      {v.replace(/_/g, ' ')}
    </span>
  )
}
