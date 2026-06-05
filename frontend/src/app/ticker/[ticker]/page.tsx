import Link from 'next/link'
import { MarketPriceChart } from '@/components/charts/MarketPriceChart'
import { Panel } from '@/components/ui/Panel'
import { MetricTile } from '@/components/ui/MetricTile'
import { ClassificationBadge } from '@/components/ui/Badges'
import { EmptyState } from '@/components/ui/States'
import { BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { HelpTip } from '@/components/ui/HelpTip'
import { define } from '@/lib/glossary'
import { getApiBase, fetchJson } from '@/lib/api'
import { isNum, money, num, pct, pctFrac, safeDate } from '@/lib/format'

export const dynamic = 'force-dynamic'

type AdvScore = {
  score?: number
  confidence?: number
  explanation?: string
  inputs_used?: Record<string, number>
  missing_inputs?: string[]
}
type Valuation = {
  ticker?: string
  classification?: string
  confidence?: number
  reason?: string
  generated_at?: string
  metrics?: Record<string, number>
  advanced_scores?: Record<string, AdvScore>
  thesis_invalidation_triggers?: string[]
  monitor_next?: string[]
  red_flags?: string[]
  missing_data?: string[]
  m4_memo_status?: string
}

// Pretty labels for the score keys the backend emits.
const SCORE_LABELS: Record<string, string> = {
  thesis_fragility: 'Thesis Fragility',
  expectations_gap: 'Expectations Gap',
  operating_leverage_convexity: 'Operating Leverage Convexity',
  reflexivity_risk: 'Financial Reflexivity (MVP)',
  misunderstood_change: 'Misunderstood Change',
}

// Plain-English help for the score keys a beginner won't recognise.
const SCORE_HELP: Record<string, string | undefined> = {
  thesis_fragility: define('thesis fragility'),
  expectations_gap: define('expectations gap'),
}

// Direction of each 0–100 score: does a HIGH value mean good or risk?
// Mirrors backend app/scoring/calibration.py. 'better' = high is good.
const SCORE_DIRECTION: Record<string, 'better' | 'risk'> = {
  operating_leverage_convexity: 'better',
  misunderstood_change: 'better',
  perception_shift: 'better',
  reflexivity_risk: 'risk',
  expectations_gap: 'risk',
  thesis_fragility: 'risk',
  narrative_entropy: 'risk',
}

export default async function TickerPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params
  const symbol = ticker.toUpperCase()

  const [valuation, quote] = await Promise.all([
    fetchJson<Valuation>(`/api/tickers/${symbol}/valuation`),
    fetchJson<{ c?: number; dp?: number; provider_used?: string }>(`/api/market/quote/${symbol}`),
  ])

  if (!valuation) {
    return (
      <div className="p-3">
        <Panel title={`${symbol} — research`}>
          <EmptyState
            title={`No valuation scorecard for ${symbol}`}
            hint={
              <>
                The deterministic valuation scorecard has not been generated for this ticker yet. Source endpoint:{' '}
                <code className="text-faint">{getApiBase()}/api/tickers/{symbol}/valuation</code>.
              </>
            }
          />
          <div className="mt-3 text-center">
            <Link href="/portfolio" className="text-2xs text-accent hover:underline">← Back to portfolio</Link>
          </div>
        </Panel>
      </div>
    )
  }

  const m = valuation.metrics ?? {}
  const adv = valuation.advanced_scores ?? {}
  const impliedGrowth = adv.expectations_gap?.inputs_used?.implied_growth // correct nested path
  const generated = safeDate(valuation.generated_at)
  const price = isNum(quote?.c) ? quote!.c : undefined

  return (
    <div className="space-y-4 px-4 py-4">
      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{symbol}</h1>
          <ClassificationBadge value={valuation.classification} />
          {isNum(valuation.confidence) && (
            <span className="text-2xs text-mutedForeground">confidence {pctFrac(valuation.confidence, { decimals: 0 })}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-2xs text-mutedForeground">
          {isNum(price) && <span className="num text-sm font-semibold text-foreground">{money(price)}</span>}
          {quote?.provider_used && <span>via {quote.provider_used}</span>}
          {generated && <span>· generated {generated}</span>}
        </div>
      </div>

      <BeginnerOnly>
        <HelpBox answers="Is this company strong, risky, or overpriced?">
          The badge and thesis give the verdict; the scores and metrics below show why. Hover any “?” to learn a term.
        </HelpBox>
      </BeginnerOnly>

      {valuation.reason && (
        <div className="accent-stripe rounded-md border border-white/[0.06] bg-panel pl-3.5 pr-3 py-2.5 text-sm leading-relaxed text-foreground/90">
          <span className="text-2xs font-semibold uppercase tracking-label text-mutedForeground">Thesis · </span>
          {valuation.reason}
        </div>
      )}

      {/* key metrics */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
        <MetricTile label="Live Price" value={isNum(price) ? money(price) : '—'} missingReason="no live quote from provider" />
        <MetricTile label="P / E" value={isNum(m.pe_ratio) ? `${num(m.pe_ratio)}×` : '—'} missingReason="not in scorecard" />
        <MetricTile label="Gross Margin" value={isNum(m.gross_margin) ? pctFrac(m.gross_margin) : '—'} missingReason="not in scorecard" />
        <MetricTile label="FCF Margin" value={isNum(m.fcf_margin) ? pctFrac(m.fcf_margin) : '—'} missingReason="not in scorecard" />
        <MetricTile label="Debt / Equity" value={isNum(m.debt_to_equity) ? num(m.debt_to_equity) : '—'} missingReason="not in scorecard" />
        <MetricTile label="Current Ratio" value={isNum(m.current_ratio) ? num(m.current_ratio) : '—'} missingReason="not in scorecard" />
        <MetricTile
          label="Implied Growth (5Y)"
          value={isNum(impliedGrowth) ? pctFrac(impliedGrowth) : '—'}
          missingReason="no reverse-DCF inputs in scorecard"
        />
      </div>

      {/* chart */}
      <div className="overflow-hidden rounded-md border border-white/[0.07] bg-panel shadow-elev">
        <MarketPriceChart ticker={symbol} height={420} defaultTimeframe="6M" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* advanced scores — uniform 0..100 scale as clean meter rows */}
        <Panel title="Asterion scorecard (0–100)">
          {Object.keys(adv).length === 0 ? (
            <EmptyState title="No advanced scores" />
          ) : (
            <div className="space-y-3">
              {Object.entries(adv).map(([key, s]) => {
                const n = isNum(s.score) ? Math.max(0, Math.min(100, s.score!)) : null
                const barTone = !isNum(n) ? 'bg-faint/40' : n! >= 66 ? 'bg-up/70' : n! >= 33 ? 'bg-warn/70' : 'bg-down/70'
                return (
                  <div key={key}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                        {SCORE_LABELS[key] ?? key.replace(/_/g, ' ')}
                        {SCORE_HELP[key] && <HelpTip text={SCORE_HELP[key]!} label={SCORE_LABELS[key] ?? key} />}
                        {SCORE_DIRECTION[key] && (
                          <span
                            className={`rounded px-1 py-0.5 text-2xs uppercase tracking-label ${
                              SCORE_DIRECTION[key] === 'better'
                                ? 'bg-up/10 text-up'
                                : 'bg-warn/10 text-warn'
                            }`}
                            title={
                              SCORE_DIRECTION[key] === 'better'
                                ? 'High is good — a higher score is favourable'
                                : 'High is risk — a higher score is a caution'
                            }
                          >
                            {SCORE_DIRECTION[key] === 'better' ? 'high = good' : 'high = risk'}
                          </span>
                        )}
                      </span>
                      <span className="flex items-baseline gap-2">
                        <span className="num text-sm font-semibold tabular-nums">
                          {isNum(n) ? n!.toFixed(1) : '—'}
                          <span className="ml-0.5 text-2xs font-normal text-faint">/100</span>
                        </span>
                        {isNum(s.confidence) && (
                          <span className="text-2xs text-faint">conf {pctFrac(s.confidence, { decimals: 0 })}</span>
                        )}
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.04]">
                      <div className={`h-full rounded-full ${barTone}`} style={{ width: `${isNum(n) ? n : 0}%` }} />
                    </div>
                    {s.explanation && <div className="mt-1 text-2xs leading-relaxed text-faint">{s.explanation}</div>}
                  </div>
                )
              })}
            </div>
          )}
        </Panel>

        {/* thesis risks */}
        <Panel title="Thesis risks">
          <div className="space-y-3">
            <div>
              <div className="mb-1 text-2xs uppercase tracking-wider text-down">Invalidation triggers</div>
              {valuation.thesis_invalidation_triggers?.length ? (
                <ul className="space-y-1">
                  {valuation.thesis_invalidation_triggers.map((t, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <span className="text-down">▸</span>
                      {t}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-2xs text-faint">none recorded</div>
              )}
            </div>
            <div>
              <div className="mb-1 text-2xs uppercase tracking-wider text-warn">Monitor next</div>
              {valuation.monitor_next?.length ? (
                <ul className="space-y-1">
                  {valuation.monitor_next.map((t, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <span className="text-warn">▸</span>
                      {t}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-2xs text-faint">none recorded</div>
              )}
            </div>
            {valuation.red_flags && valuation.red_flags.length > 0 && (
              <div>
                <div className="mb-1 text-2xs uppercase tracking-wider text-down">Red flags</div>
                <div className="flex flex-wrap gap-1">
                  {valuation.red_flags.map((f, i) => (
                    <span key={i} className="rounded border border-down/30 bg-down/10 px-1.5 py-0.5 text-2xs text-down">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* missing data — honest */}
      <Panel title="Missing data">
        {valuation.missing_data && valuation.missing_data.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {valuation.missing_data.map((item, i) => (
              <span key={i} className="rounded border border-down/30 bg-down/10 px-2 py-0.5 text-2xs text-down">
                {item}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-2xs text-up">No critical missing data flagged by report generation.</div>
        )}
        <div className="mt-2 text-2xs text-faint">
          Memo status: {valuation.m4_memo_status ?? 'Unavailable'}. Metrics not present in the scorecard (e.g. EV/FCF,
          EV/EBITDA) are not invented here — they read “not in scorecard”.
        </div>
      </Panel>
    </div>
  )
}
