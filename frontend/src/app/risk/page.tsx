import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { HBarList } from '@/components/portfolio/HBar'
import { DataQualityBadge, SeverityChip, type Severity } from '@/components/ui/Badges'
import { ErrorBanner } from '@/components/ui/States'
import { BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { HelpTip } from '@/components/ui/HelpTip'
import { define } from '@/lib/glossary'
import { fetchJson, getApiBase } from '@/lib/api'
import { isNum, pctFrac } from '@/lib/format'

export const dynamic = 'force-dynamic'

type Cov = {
  ticker: string
  data_quality: string
  has_facts: boolean
  has_ratios: boolean
  has_rag: boolean
  has_memo: boolean
  has_valuation: boolean
}

function RiskCard({
  severity,
  title,
  children,
}: {
  severity: Severity
  title: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Panel title={title} right={<SeverityChip level={severity} />}>
      {children}
    </Panel>
  )
}

export default async function RiskPage() {
  const [latest, live, coverageResp] = await Promise.all([
    fetchJson<any>('/api/portfolio/latest'),
    fetchJson<any>('/api/portfolio/live'),
    fetchJson<{ coverage: Cov[] }>('/api/portfolio/coverage'),
  ])

  if (!latest) {
    return (
      <div className="p-3">
        <ErrorBanner title="Risk cockpit needs the backend" detail={`No data from ${getApiBase()}/api/portfolio/latest.`} />
      </div>
    )
  }

  const summary = latest.summary ?? {}
  const themes: Record<string, number> = latest.theme_concentration ?? {}
  const warnings: string[] = latest.policy_warnings ?? []
  const coverage = coverageResp?.coverage ?? []
  const holdings: { ticker: string; weight?: number }[] = live?.holdings ?? []

  const top5 = [...holdings]
    .filter((h) => isNum(h.weight))
    .sort((a, b) => (b.weight as number) - (a.weight as number))
    .slice(0, 5)
  const top5Sum = top5.reduce((s, h) => s + (h.weight as number), 0)

  const aiExposure =
    (themes['AI/semiconductor'] ?? 0) + (themes['AI/software'] ?? 0) + (themes['data center infrastructure'] ?? 0)
  const coreEtf = summary.core_etf_exposure ?? 0
  const spec = summary.speculative_exposure ?? 0
  const valRisk = summary.high_valuation_risk_positions ?? 0

  const themeRows = Object.entries(themes)
    .sort(([, a], [, b]) => b - a)
    .map(([t, w]) => ({ label: t.split('/')[0], value: w * 100, valueText: pctFrac(w) }))

  const dataGaps = coverage.filter((c) => !c.has_ratios || !c.has_rag || !c.has_memo)

  // plain-english diagnosis lines
  const diagnosis: string[] = []
  diagnosis.push(
    top5Sum > 0.5
      ? `Concentrated: your top 5 names are ${pctFrac(top5Sum, { decimals: 0 })} of the book — a few positions drive performance.`
      : `Reasonably spread: top 5 names are ${pctFrac(top5Sum, { decimals: 0 })} of the book.`,
  )
  if (coreEtf < 0.3) diagnosis.push(`Light on protection: only ${pctFrac(coreEtf, { decimals: 0 })} in broad ETFs (floor is 30%).`)
  if (aiExposure > 0.3) diagnosis.push(`Heavy AI/semis tilt at ${pctFrac(aiExposure, { decimals: 0 })} — correlated single-theme exposure.`)
  if (valRisk > 0) diagnosis.push(`${valRisk} holdings carry stretched-valuation flags.`)
  if (dataGaps.length) diagnosis.push(`${dataGaps.length} tickers are only partially covered (missing ratios/RAG/memo), so policy checks on them are incomplete.`)

  // severity grades for each diagnostic module
  const concSev: Severity = top5Sum > 0.5 ? 'high' : top5Sum > 0.35 ? 'medium' : 'low'
  const themeSev: Severity = aiExposure > 0.4 || coreEtf < 0.3 ? 'high' : aiExposure > 0.3 ? 'medium' : 'low'
  const valSev: Severity = valRisk >= 3 ? 'high' : valRisk >= 1 ? 'medium' : 'low'
  const dataSev: Severity = dataGaps.length > 8 ? 'high' : dataGaps.length > 0 ? 'medium' : 'low'

  return (
    <div className="space-y-4 px-4 py-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Risk Cockpit</h1>
        <p className="mt-0.5 text-xs text-mutedForeground">Diagnostic console — what is wrong with this portfolio, in plain English.</p>
      </div>

      <BeginnerOnly>
        <HelpBox answers="What could hurt me?">
          Four risks, each graded low / medium / high. Read the diagnosis first, then the cards.
        </HelpBox>
      </BeginnerOnly>

      <Panel title="Diagnosis" accent>
        <ul className="space-y-2 text-sm leading-relaxed">
          {diagnosis.map((d, i) => (
            <li key={i} className="flex gap-2.5">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span className="text-foreground/90">{d}</span>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RiskCard severity={concSev} title="Concentration risk">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span>Top 5 concentration</span>
            <span className={`num font-semibold ${top5Sum > 0.5 ? 'text-down' : 'text-up'}`}>{pctFrac(top5Sum)}</span>
          </div>
          <HBarList
            rows={top5.map((h) => ({ label: h.ticker, value: (h.weight as number) * 100, valueText: pctFrac(h.weight) }))}
            tone="accent"
            linkBase="/ticker/"
          />
        </RiskCard>

        <RiskCard severity={themeSev} title="Theme risk">
          <HBarList rows={themeRows} tone="warn" />
          <div className="mt-2 grid grid-cols-2 gap-2 text-2xs">
            <div className="flex justify-between"><span className="text-mutedForeground">AI / semis</span><span className="num">{pctFrac(aiExposure)}</span></div>
            <div className="flex justify-between"><span className="text-mutedForeground">Core ETF</span><span className={`num ${coreEtf < 0.3 ? 'text-warn' : 'text-up'}`}>{pctFrac(coreEtf)}</span></div>
            <div className="flex justify-between"><span className="text-mutedForeground">Speculative</span><span className="num">{pctFrac(spec)}</span></div>
          </div>
        </RiskCard>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RiskCard
          severity={valSev}
          title={<span className="inline-flex items-center gap-1">Valuation risk <HelpTip text={define('valuation risk') ?? ''} label="valuation risk" /></span>}
        >
          <div className="mb-2 flex items-center justify-between text-sm">
            <span>Holdings flagged</span>
            <span className={`num font-semibold ${valRisk > 0 ? 'text-warn' : 'text-up'}`}>{valRisk}</span>
          </div>
          <p className="text-2xs text-mutedForeground">
            Flagged names trade at stretched multiples and are vulnerable to rate shocks or small earnings misses. Open a
            ticker to see its expectations gap and thesis fragility.
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(latest.m6_scorecards_integrated ?? []).map((t: string) => (
              <Link key={t} href={`/ticker/${t}`} className="num rounded border border-warn/30 bg-warn/10 px-1.5 py-0.5 text-2xs text-warn hover:border-warn">
                {t}
              </Link>
            ))}
          </div>
        </RiskCard>

        <RiskCard severity={dataSev} title="Data risk — blind spots">
          {dataGaps.length === 0 ? (
            <div className="text-2xs text-up">Full coverage across holdings.</div>
          ) : (
            <table className="w-full text-sm">
              <tbody>
                {dataGaps.slice(0, 8).map((c) => (
                  <tr key={c.ticker} className="border-b border-border/50 last:border-0">
                    <td className="py-1.5">
                      <Link href={`/ticker/${c.ticker}`} className="num font-medium hover:text-accent">{c.ticker}</Link>
                    </td>
                    <td className="py-1.5 text-right text-2xs text-faint">
                      {[!c.has_ratios && 'ratios', !c.has_rag && 'RAG', !c.has_memo && 'memo'].filter(Boolean).join(' · ')}
                    </td>
                    <td className="py-1.5 pl-2 text-right">
                      <DataQualityBadge quality={c.data_quality} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </RiskCard>
      </div>

      {warnings.length > 0 && (
        <details className="group overflow-hidden rounded-md border border-white/[0.06] bg-panel">
          <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-2xs font-semibold uppercase tracking-label text-mutedForeground transition-colors hover:text-foreground">
            <span>Raw policy-engine warnings ({warnings.length})</span>
            <span className="text-faint transition-transform group-open:rotate-90">›</span>
          </summary>
          <ul className="space-y-1 border-t border-white/[0.05] px-3 py-2">
            {warnings.map((w, i) => (
              <li key={i} className="flex gap-2 text-2xs text-warn">
                <span>⚠</span>
                {w.replace(/^Policy Warning:\s*/, '')}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
