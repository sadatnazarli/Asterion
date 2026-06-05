import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { ErrorBanner } from '@/components/ui/States'
import { fetchJson } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Finding = { category: string; domain: string; level: string; rationale: string; evidence: string[] }
type FinancialSummary = {
  available: boolean
  asterion_classification: string | null
  confidence: number
  findings: Finding[]
  missing: string[]
  headline: string
}
type ComplianceSummary = {
  provider_status: string
  match_status: string
  confidence: number
  findings: Finding[]
  matches: { name: string; categories: string[]; source: string | null }[]
  missing: string[]
  headline: string
}
type DecisionReport = {
  entity_name: string
  ticker: string | null
  is_public: boolean
  financial_summary: FinancialSummary
  compliance_summary: ComplianceSummary
  combined_risk_level: string
  classification: string
  confidence: number
  missing_data: string[]
  evidence_links: string[]
  recommended_next_research_steps: string[]
  what_would_change_conclusion: string[]
  disclaimer: string
}

const LEVEL_TONE: Record<string, string> = {
  none: 'text-up',
  low: 'text-up',
  medium: 'text-warn',
  high: 'text-down',
  critical: 'text-down',
  unknown: 'text-faint',
}

const CLASS_CHIP: Record<string, string> = {
  clear_for_research: 'bg-up/12 text-up ring-1 ring-up/25',
  financial_risk_watchlist: 'bg-warn/15 text-warn ring-1 ring-warn/25',
  compliance_risk_watchlist: 'bg-warn/15 text-warn ring-1 ring-warn/25',
  combined_risk_watchlist: 'bg-down/12 text-down ring-1 ring-down/25',
  insufficient_data: 'bg-white/[0.06] text-mutedForeground',
  blocked_by_compliance_signal: 'bg-down/20 text-down ring-1 ring-down/40',
}

function FindingRow({ f }: { f: Finding }) {
  return (
    <div className="border-l-2 border-white/10 pl-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-foreground">{f.category.replace(/_/g, ' ')}</span>
        <span className={`text-2xs font-semibold uppercase ${LEVEL_TONE[f.level] ?? 'text-faint'}`}>{f.level}</span>
      </div>
      {f.rationale && <p className="mt-0.5 text-2xs text-mutedForeground">{f.rationale}</p>}
    </div>
  )
}

export default async function DecisionPage({ params }: { params: Promise<{ entity: string }> }) {
  const { entity } = await params
  const r = await fetchJson<DecisionReport>(`/api/decision/${encodeURIComponent(entity)}`)

  if (!r) {
    return (
      <div className="p-3">
        <ErrorBanner
          title="No decision report"
          detail={`Run scripts/generate_decision_report.py ${entity} to generate it.`}
        />
      </div>
    )
  }

  const fin = r.financial_summary
  const comp = r.compliance_summary

  return (
    <div className="space-y-3 p-3">
      {/* Decision-intelligence banner */}
      <div className="rounded-md border border-accent/30 bg-accent/[0.06] px-3 py-2">
        <div className="text-2xs font-semibold uppercase tracking-label text-accent">
          Decision Intelligence — Financial + Compliance
        </div>
        <div className="mt-0.5 text-2xs text-mutedForeground">
          Merges Asterion financial risk with Verifex compliance/entity risk. Research only — no buy/sell.
        </div>
      </div>

      <Panel
        accent
        title={`${r.entity_name}${r.ticker ? ` · ${r.ticker}` : ''}`}
        right={<span className="num text-2xs text-faint">conf {r.confidence.toFixed(2)}</span>}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className={`inline-block rounded px-2 py-0.5 text-2xs font-semibold ${CLASS_CHIP[r.classification] ?? 'bg-white/[0.06] text-mutedForeground'}`}>
            {r.classification.replace(/_/g, ' ')}
          </span>
          <span className="text-2xs text-faint">
            combined risk <span className={LEVEL_TONE[r.combined_risk_level] ?? 'text-faint'}>{r.combined_risk_level}</span>
            {' '}· {r.is_public ? 'public' : 'private'} entity
          </span>
        </div>
      </Panel>

      <div className="grid gap-3 lg:grid-cols-2">
        {/* Financial */}
        <Panel title="Financial risk (Asterion)">
          <p className="text-xs text-mutedForeground">{fin.headline}</p>
          {fin.available ? (
            <div className="mt-2 space-y-2">
              {fin.findings.map((f) => (
                <FindingRow key={f.category} f={f} />
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-faint">Asterion scorecard not found — financial risk not assessed.</p>
          )}
        </Panel>

        {/* Compliance */}
        <Panel title="Compliance / entity risk (Verifex)">
          <div className="text-2xs text-faint">
            provider <span className="text-mutedForeground">{comp.provider_status}</span> · match{' '}
            <span className="text-mutedForeground">{comp.match_status}</span>
          </div>
          <p className="mt-1 text-xs text-mutedForeground">{comp.headline}</p>
          {comp.findings.length > 0 && (
            <div className="mt-2 space-y-2">
              {comp.findings.map((f) => (
                <FindingRow key={f.category} f={f} />
              ))}
            </div>
          )}
          {comp.matches.length > 0 && (
            <div className="mt-2 space-y-0.5">
              {comp.matches.slice(0, 6).map((m, i) => (
                <div key={i} className="text-2xs text-faint">
                  {m.name} · {(m.categories || []).join(', ') || '—'} · {m.source ?? 'verifex'}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Missing + evidence */}
      <div className="grid gap-3 sm:grid-cols-2">
        <Panel title="Missing data (shown, not faked)">
          <ul className="space-y-0.5 text-2xs text-warn/80">
            {(r.missing_data.length ? r.missing_data : ['—']).map((d) => (
              <li key={d}>• {d}</li>
            ))}
          </ul>
        </Panel>
        <Panel title="Evidence">
          <ul className="space-y-0.5 text-2xs text-mutedForeground">
            {(r.evidence_links.length ? r.evidence_links : ['—']).map((d) => (
              <li key={d}>• {d}</li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* Next steps + what would change */}
      <div className="grid gap-3 sm:grid-cols-2">
        <Panel title="Recommended next research steps">
          <ul className="space-y-1 text-2xs text-mutedForeground">
            {r.recommended_next_research_steps.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Panel>
        <Panel title="What would change the conclusion">
          <ul className="space-y-1 text-2xs text-mutedForeground">
            {r.what_would_change_conclusion.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Panel>
      </div>

      <p className="px-1 text-2xs text-faint">
        {r.disclaimer} See also{' '}
        <Link href="/reports" className="text-accent hover:underline">
          /reports
        </Link>
        .
      </p>
    </div>
  )
}
