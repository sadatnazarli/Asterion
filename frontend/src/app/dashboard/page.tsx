import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { MetricTile } from '@/components/ui/MetricTile'
import { DataQualityBadge } from '@/components/ui/Badges'
import { HBarList } from '@/components/portfolio/HBar'
import { TodaysReadout } from '@/components/portfolio/TodaysReadout'
import { ContributorColumns } from '@/components/portfolio/Contributors'
import { ErrorBanner } from '@/components/ui/States'
import { BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { ReadingOrder, AsterionExplains, ActionChecklist } from '@/components/onboarding/DashboardGuides'
import { fetchJson, getApiBase } from '@/lib/api'
import { computeContributors, mainRiskText, nextActionText, type Contributors } from '@/lib/insights'
import { define } from '@/lib/glossary'
import { compactMoney, money, pct, pctFrac } from '@/lib/format'

export const dynamic = 'force-dynamic'

type Cov = { ticker: string; data_quality: string; has_ratios: boolean; has_rag: boolean; has_valuation: boolean }

export default async function DashboardPage() {
  const [live, latest, coverageResp, providers, contribResp] = await Promise.all([
    fetchJson<any>('/api/portfolio/live'),
    fetchJson<any>('/api/portfolio/latest'),
    fetchJson<{ coverage: Cov[] }>('/api/portfolio/coverage'),
    fetchJson<any>('/api/system/providers'),
    fetchJson<Contributors>('/api/portfolio/contributors'),
  ])

  if (!live || !latest) {
    return (
      <div className="p-3">
        <ErrorBanner title="Dashboard needs the backend" detail={`No portfolio data from ${getApiBase()}.`} />
      </div>
    )
  }

  const total = live.total_value ?? 0
  const dailyPnl = live.daily_pnl ?? 0
  const dailyPct = live.daily_pnl_pct ?? 0
  const summary = latest.summary ?? {}
  const themes: Record<string, number> = latest.theme_concentration ?? {}
  const warnings: string[] = latest.policy_warnings ?? []
  const coverage = coverageResp?.coverage ?? []
  const holdings: { ticker: string; current_value: number; daily_change_pct?: number | null }[] = live.holdings ?? []

  const contributors: Contributors = contribResp ?? computeContributors(holdings, dailyPnl, total)

  const aiExposure =
    (themes['AI/semiconductor'] ?? 0) + (themes['AI/software'] ?? 0) + (themes['data center infrastructure'] ?? 0)
  const coreEtf = summary.core_etf_exposure ?? 0
  const valRisk = summary.high_valuation_risk_positions ?? 0
  const missingRatios = coverage.filter((c) => c.has_valuation && !c.has_ratios).length
  const noRag = coverage.filter((c) => c.has_valuation && !c.has_rag).length
  const finnhubConfigured = providers?.finnhub?.configured ?? false

  const mainRisk = mainRiskText(summary, themes)
  const nextAction = nextActionText({ costBasisMissing: !!live.cost_basis_missing, missingRatios, noRag, valRisk, finnhubConfigured })

  const topHoldings = [...holdings]
    .sort((a, b) => b.current_value - a.current_value)
    .slice(0, 8)
    .map((h) => ({ label: h.ticker, value: h.current_value, valueText: compactMoney(h.current_value) }))
  const themeRows = Object.entries(themes)
    .sort(([, a], [, b]) => b - a)
    .map(([t, w]) => ({ label: t.split('/')[0], value: w * 100, valueText: pctFrac(w) }))

  // beginner "Asterion explains" inputs
  const sortedValues = [...holdings].sort((a, b) => b.current_value - a.current_value)
  const top5Value = sortedValues.slice(0, 5).reduce((s, h) => s + (h.current_value ?? 0), 0)
  const concentrated = total > 0 && top5Value / total > 0.5
  const topNegative = contributors.top_negative.map((r) => r.ticker)

  const actions: { text: string; href: string }[] = []
  if (live.cost_basis_missing) actions.push({ text: 'Add cost basis — P/L is estimated without share counts', href: '/portfolio' })
  if (missingRatios) actions.push({ text: `Compute ratios for ${missingRatios} tickers`, href: '/coverage' })
  if (noRag) actions.push({ text: `Run RAG/memos for ${noRag} holdings`, href: '/coverage' })
  if (valRisk) actions.push({ text: `Review ${valRisk} valuation-risk holdings`, href: '/risk' })
  if (!finnhubConfigured) actions.push({ text: 'Add FINNHUB_API_KEY for live streaming', href: '/system' })

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Portfolio Intelligence</h1>
        <p className="mt-0.5 text-xs text-mutedForeground">Plain-English explanation of what you own and what it&apos;s doing.</p>
      </div>

      <BeginnerOnly>
        <HelpBox answers="What happened to my portfolio today?">
          New here? Read the steps below in order, then look at the numbers.
        </HelpBox>
      </BeginnerOnly>

      <BeginnerOnly>
        <ReadingOrder />
      </BeginnerOnly>

      {/* 1. Today's summary */}
      <TodaysReadout
        totalValue={total}
        dailyPnl={dailyPnl}
        dailyPnlPct={dailyPct}
        contributors={contributors}
        mainRisk={mainRisk}
        nextAction={nextAction}
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile
          label="Total value"
          value={money(total)}
          help={define('total value')}
          explain="Everything you own added up at the latest prices."
        />
        <MetricTile
          label="Today P/L"
          value={`${dailyPnl >= 0 ? '+' : ''}${money(dailyPnl).replace('$-', '-$')}`}
          sub={pct(dailyPct, { signed: true })}
          tone={dailyPnl >= 0 ? 'up' : 'down'}
          help={define('today p/l')}
          explain="How much your portfolio moved today — one day is noise, not the thesis."
        />
        <MetricTile
          label="Core ETF"
          value={pctFrac(coreEtf)}
          tone={coreEtf < 0.3 ? 'warn' : 'up'}
          sub="target ≥ 30%"
          help={define('core etf exposure')}
          explain="Broad index funds that cushion you; aim for at least 30%."
        />
        <MetricTile
          label="AI / semis"
          value={pctFrac(aiExposure)}
          tone={aiExposure > 0.4 ? 'warn' : 'default'}
          help={define('ai / semiconductor exposure')}
          explain="How concentrated you are in the AI/chip theme — these move together."
        />
      </div>

      <BeginnerOnly>
        <AsterionExplains
          concentrated={concentrated}
          coreEtfPct={pctFrac(coreEtf)}
          coreBelowTarget={coreEtf < 0.3}
          topNegative={topNegative}
          dailyUp={dailyPnl >= 0}
        />
      </BeginnerOnly>

      {/* 2. Why it moved */}
      <Panel title="Why it moved today">
        <ContributorColumns positive={contributors.top_positive} negative={contributors.top_negative} />
        <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 border-t border-border pt-2 text-2xs text-mutedForeground">
          <span>Estimated daily P/L: <span className="num">{money(contributors.sum_contributions).replace('$-', '-$')}</span></span>
          <span>Reported: <span className="num">{money(contributors.daily_pnl_reported).replace('$-', '-$')}</span></span>
          <span>Unexplained: <span className="num">{money(contributors.unexplained_difference).replace('$-', '-$')}</span></span>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 3. Biggest risks */}
        <Panel title="Biggest risks" right={<Link href="/risk" className="text-2xs text-accent hover:underline">Risk cockpit →</Link>}>
          {warnings.length === 0 ? (
            <div className="text-2xs text-up">No policy warnings.</div>
          ) : (
            <ul className="space-y-1.5">
              {warnings.map((w, i) => (
                <li key={i} className="flex gap-2 text-sm text-warn">
                  <span>⚠</span>
                  {w.replace(/^Policy Warning:\s*/, '')}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {/* 4. What should I do now? — research actions only */}
        <ActionChecklist items={actions} />
      </div>

      {/* 5. Allocation snapshot */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Top holdings — by value">
          <HBarList rows={topHoldings} tone="accent" linkBase="/ticker/" />
        </Panel>
        <Panel title="Theme exposure">
          <HBarList rows={themeRows} tone="warn" />
        </Panel>
      </div>

      {/* 6. Missing data */}
      <Panel title="Missing data">
        <div className="flex flex-wrap gap-1.5">
          {coverage.map((c) => (
            <Link
              key={c.ticker}
              href={`/ticker/${c.ticker}`}
              className="flex items-center gap-1.5 rounded border border-white/[0.06] bg-panel2 px-2 py-1 transition-colors hover:border-accent/50"
            >
              <span className="num text-2xs font-semibold">{c.ticker}</span>
              <DataQualityBadge quality={c.data_quality} />
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  )
}
