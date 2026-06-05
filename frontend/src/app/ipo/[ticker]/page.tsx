import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { ErrorBanner } from '@/components/ui/States'
import { fetchJson } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Metrics = Record<string, number | null>
type Scenario = {
  scenario: string
  revenue_cagr: number
  target_fcf_margin: number
  terminal_fcf_multiple: number
  pv_enterprise_value_musd: number
  gap_vs_ipo_ev_pct: number | null
}
type Risk = { category: string; level: string; rationale: string }
type Filing = { form: string; filing_date: string; url: string | null }
type IpoScorecard = {
  ticker: string
  classification: string
  confidence: number
  thesis: string
  disclaimer: string
  verification: {
    filing_found: boolean
    registrant_name: string | null
    cik: string | null
    proposed_ticker: string | null
    filings: Filing[]
  }
  valuation: { can_value: boolean; method: string; metrics: Metrics; scenarios: Scenario[] }
  risks: Risk[]
  key_risks: string[]
  missing_data: string[]
  must_verify: string[]
  monitoring_checklist: string[]
}

const RISK_TONE: Record<string, string> = {
  high: 'text-down',
  elevated: 'text-warn',
  moderate: 'text-mutedForeground',
  low: 'text-up',
  unknown: 'text-faint',
}

function fmtT(musd: number | null | undefined): string {
  if (musd == null) return '—'
  if (Math.abs(musd) >= 1e6) return `$${(musd / 1e6).toFixed(2)}T`
  if (Math.abs(musd) >= 1e3) return `$${(musd / 1e3).toFixed(1)}B`
  return `$${Math.round(musd).toLocaleString()}M`
}

export default async function IpoPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params
  const sc = await fetchJson<IpoScorecard>(`/api/ipo/${ticker.toUpperCase()}`)

  if (!sc) {
    return (
      <div className="p-3">
        <ErrorBanner
          title="No IPO scorecard"
          detail={`Run scripts/analyze_ipo_candidate.py ${ticker.toUpperCase()} to generate it.`}
        />
      </div>
    )
  }

  const m = sc.valuation.metrics
  const evs = m.ev_to_revenue ?? m.price_to_sales

  return (
    <div className="space-y-3 p-3">
      {/* IPO mode banner */}
      <div className="rounded-md border border-gold/30 bg-gold/[0.06] px-3 py-2">
        <div className="text-2xs font-semibold uppercase tracking-label text-gold">
          IPO / Private Company Mode
        </div>
        <div className="mt-0.5 text-2xs text-mutedForeground">
          Not a normal public ticker analysis. {sc.disclaimer}
        </div>
      </div>

      <Panel
        accent
        title={`${sc.ticker} — IPO Scorecard`}
        right={
          <span className="num text-2xs text-faint">
            {sc.verification.proposed_ticker ?? '—'} · conf {sc.confidence.toFixed(2)}
          </span>
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-block rounded bg-warn/15 px-2 py-0.5 text-2xs font-medium text-warn ring-1 ring-warn/25">
            {sc.classification}
          </span>
          <span className="text-2xs text-faint">research-only — no buy/sell</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-mutedForeground">{sc.thesis}</p>
      </Panel>

      {/* Verification */}
      <Panel title="Source verification (SEC EDGAR)">
        <div className="text-xs text-mutedForeground">
          Official filing:{' '}
          <span className={sc.verification.filing_found ? 'text-up' : 'text-down'}>
            {sc.verification.filing_found ? 'VERIFIED' : 'NOT FOUND'}
          </span>{' '}
          · {sc.verification.registrant_name ?? '—'} · CIK {sc.verification.cik ?? '—'}
        </div>
        <div className="mt-2 space-y-1">
          {sc.verification.filings.slice(0, 4).map((f, i) => (
            <div key={i} className="text-2xs text-faint">
              {f.form} · {f.filing_date}{' '}
              {f.url && (
                <a href={f.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                  view filing →
                </a>
              )}
            </div>
          ))}
        </div>
      </Panel>

      {/* Valuation */}
      <Panel title="Valuation">
        {sc.valuation.can_value ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs sm:grid-cols-3">
            <Metric label="Implied market cap" value={fmtT(m.implied_market_cap_musd)} />
            <Metric label="Enterprise value" value={fmtT(m.enterprise_value_musd)} />
            <Metric label="EV / Revenue" value={evs ? `${Math.round(evs)}x` : '—'} tone="down" />
            <Metric label="Price / Sales" value={m.price_to_sales ? `${Math.round(m.price_to_sales)}x` : '—'} />
            <Metric
              label="Operating margin"
              value={m.operating_margin != null ? `${Math.round(m.operating_margin * 100)}%` : '—'}
            />
            <Metric
              label="Offering dilution"
              value={m.offering_dilution_pct != null ? `${(m.offering_dilution_pct * 100).toFixed(1)}%` : '—'}
            />
          </div>
        ) : (
          <p className="text-xs text-faint">Valuation not computed — missing price and/or share count.</p>
        )}
        <p className="mt-2 text-2xs text-faint">method: {sc.valuation.method}</p>
      </Panel>

      {/* Scenarios */}
      {sc.valuation.scenarios.length > 0 && (
        <Panel title="Path-to-FCF scenarios (speculative — FCF unconfirmed)">
          <div className="space-y-1.5">
            {sc.valuation.scenarios.map((s) => (
              <div key={s.scenario} className="flex items-center justify-between text-xs">
                <span className="w-14 uppercase tracking-label text-mutedForeground">{s.scenario}</span>
                <span className="num text-faint">
                  CAGR {(s.revenue_cagr * 100).toFixed(0)}% · FCF {(s.target_fcf_margin * 100).toFixed(0)}% ·{' '}
                  {s.terminal_fcf_multiple}x
                </span>
                <span className="num text-foreground">{fmtT(s.pv_enterprise_value_musd)}</span>
                <span className={`num w-16 text-right ${(s.gap_vs_ipo_ev_pct ?? 0) < 0 ? 'text-down' : 'text-up'}`}>
                  {s.gap_vs_ipo_ev_pct != null ? `${(s.gap_vs_ipo_ev_pct * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-2xs text-faint">Gap = present-value EV vs the IPO enterprise value. Speculative.</p>
        </Panel>
      )}

      {/* Risks */}
      <Panel title="IPO risk engine">
        <div className="space-y-2">
          {sc.risks.map((r) => (
            <div key={r.category} className="border-l-2 border-white/10 pl-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-foreground">{r.category.replace(/_/g, ' ')}</span>
                <span className={`text-2xs font-semibold uppercase ${RISK_TONE[r.level] ?? 'text-faint'}`}>
                  {r.level}
                </span>
              </div>
              <p className="mt-0.5 text-2xs text-mutedForeground">{r.rationale}</p>
            </div>
          ))}
        </div>
      </Panel>

      {/* Missing + monitoring */}
      <div className="grid gap-3 sm:grid-cols-2">
        <Panel title="Missing data (shown, not faked)">
          <ul className="space-y-0.5 text-2xs text-warn/80">
            {sc.missing_data.map((d) => (
              <li key={d}>• {d}</li>
            ))}
          </ul>
        </Panel>
        <Panel title="Monitoring checklist">
          <ul className="space-y-0.5 text-2xs text-mutedForeground">
            {sc.monitoring_checklist.map((d) => (
              <li key={d}>• {d}</li>
            ))}
          </ul>
        </Panel>
      </div>

      <p className="px-1 text-2xs text-faint">
        Research only — not financial advice, no buy/sell recommendation. Every figure traces to the cited SEC
        filing. See also{' '}
        <Link href="/reports" className="text-accent hover:underline">
          /reports
        </Link>
        .
      </p>
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-2xs uppercase tracking-label text-faint">{label}</div>
      <div className={`num text-sm font-semibold ${tone === 'down' ? 'text-down' : 'text-foreground'}`}>{value}</div>
    </div>
  )
}
