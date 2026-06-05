import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { ErrorBanner, EmptyState } from '@/components/ui/States'
import { fetchJson, getApiBase } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Opp = {
  ticker: string
  composite: number | null
  classification: 'screens_well' | 'neutral' | 'screens_poorly' | 'insufficient_data'
  confidence: number
  components: { value: number | null; quality: number | null; safety: number | null; change: number | null }
  drivers: string[]
  missing: string[]
  valuation_classification: string | null
  evidence: { scorecard: string; ticker_page: string }
}
type Snapshot = {
  as_of: string
  universe: number
  disclaimer: string
  weights: Record<string, number>
  opportunities: Opp[]
}

const CLASS_META: Record<Opp['classification'], { label: string; chip: string; score: string }> = {
  screens_well: { label: 'Screens well', chip: 'bg-gold/15 text-gold ring-1 ring-gold/30', score: 'text-gold' },
  neutral: { label: 'Neutral', chip: 'bg-white/[0.06] text-mutedForeground', score: 'text-foreground' },
  screens_poorly: { label: 'Screens poorly', chip: 'bg-down/12 text-down ring-1 ring-down/25', score: 'text-down' },
  insufficient_data: { label: 'Insufficient data', chip: 'bg-white/[0.04] text-faint', score: 'text-faint' },
}

function Bar({ label, value }: { label: string; value: number | null }) {
  const v = value ?? 0
  const tone = value === null ? 'bg-white/10' : v >= 65 ? 'bg-up' : v <= 35 ? 'bg-down' : 'bg-accent'
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-12 shrink-0 text-2xs uppercase tracking-label text-faint">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
        {value !== null && <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.max(2, v)}%` }} />}
      </div>
      <span className="num w-7 shrink-0 text-right text-2xs text-mutedForeground">
        {value === null ? '—' : Math.round(v)}
      </span>
    </div>
  )
}

export default async function ScannerPage() {
  const snap = await fetchJson<Snapshot>('/api/scanner/opportunities')

  if (!snap) {
    return (
      <div className="p-3">
        <ErrorBanner title="Scanner needs the backend" detail={`No data from ${getApiBase()}/api/scanner/opportunities.`} />
      </div>
    )
  }

  const opps = snap.opportunities ?? []
  const asOf = new Date(snap.as_of).toLocaleString()

  return (
    <div className="space-y-3 p-3">
      <Panel
        accent
        title="Opportunity Scanner"
        right={<span className="num text-2xs text-faint">{snap.universe} names · scanned {asOf}</span>}
      >
        <p className="text-xs leading-relaxed text-mutedForeground">{snap.disclaimer}</p>
        <p className="mt-1.5 text-2xs text-faint">
          Composite = value {pctw(snap.weights?.value)} · quality {pctw(snap.weights?.quality)} · safety{' '}
          {pctw(snap.weights?.safety)} · change {pctw(snap.weights?.change)}. Risk signals lower the score.
        </p>
      </Panel>

      {opps.length === 0 ? (
        <Panel>
          <EmptyState title="No scorecards to scan yet" hint="Generate valuation scorecards, then the scanner ranks them." />
        </Panel>
      ) : (
        <div className="space-y-2">
          {opps.map((o, i) => {
            const meta = CLASS_META[o.classification]
            return (
              <div
                key={o.ticker}
                className="group grid grid-cols-[auto_1fr_auto] items-center gap-4 rounded-md border border-white/[0.06] bg-panel px-3 py-3 transition-colors hover:bg-panel2"
              >
                {/* rank + ticker + score */}
                <div className="flex items-center gap-3">
                  <span className="num w-5 text-right text-sm text-faint">{i + 1}</span>
                  <div>
                    <Link href={o.evidence.ticker_page} className="num text-base font-bold tracking-tight text-foreground hover:text-gold">
                      {o.ticker}
                    </Link>
                    <div className="mt-0.5">
                      <span className={`inline-block rounded px-1.5 py-0.5 text-2xs font-medium ${meta.chip}`}>{meta.label}</span>
                    </div>
                  </div>
                  <div className="ml-2 text-center">
                    <div className={`num text-2xl font-bold leading-none tracking-tight ${meta.score}`}>
                      {o.composite === null ? '—' : Math.round(o.composite)}
                    </div>
                    <div className="mt-0.5 text-2xs uppercase tracking-label text-faint">screen</div>
                  </div>
                </div>

                {/* component bars */}
                <div className="grid max-w-md gap-1">
                  <Bar label="Value" value={o.components.value} />
                  <Bar label="Quality" value={o.components.quality} />
                  <Bar label="Safety" value={o.components.safety} />
                  <Bar label="Change" value={o.components.change} />
                </div>

                {/* confidence + drivers + evidence */}
                <div className="flex w-44 shrink-0 flex-col items-end gap-1 text-right">
                  <span className="num text-2xs text-mutedForeground">conf {o.confidence.toFixed(2)}</span>
                  {o.drivers.slice(0, 2).map((d) => (
                    <span key={d} className="text-2xs text-faint">{d}</span>
                  ))}
                  {o.missing.length > 0 && (
                    <span className="text-2xs text-warn/80">missing: {o.missing.join(', ')}</span>
                  )}
                  <Link href={o.evidence.ticker_page} className="mt-0.5 text-2xs text-accent hover:underline">
                    view evidence →
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function pctw(w?: number): string {
  return w == null ? '—' : `${Math.round(w * 100)}%`
}
