import { MarketTerminal } from '@/components/market/MarketTerminal'
import { ErrorBanner } from '@/components/ui/States'
import { type LiveMode } from '@/components/ui/Badges'
import { fetchJson, getApiBase } from '@/lib/api'
import { computeContributors, mainRiskText, nextActionText, type Contributors } from '@/lib/insights'

export const dynamic = 'force-dynamic'

type Cov = { ticker: string; has_valuation: boolean; has_ratios: boolean; has_rag: boolean }

export default async function MarketPage() {
  const [live, latest, coverageResp, reportsResp, providers, contribResp] = await Promise.all([
    fetchJson<any>('/api/portfolio/live'),
    fetchJson<any>('/api/portfolio/latest'),
    fetchJson<{ coverage: Cov[] }>('/api/portfolio/coverage'),
    fetchJson<any>('/api/reports'),
    fetchJson<any>('/api/system/providers'),
    fetchJson<Contributors>('/api/portfolio/contributors'),
  ])

  if (!live) {
    return (
      <div className="p-3">
        <ErrorBanner title="Market Terminal needs the backend" detail={`No data from ${getApiBase()}/api/portfolio/live.`} />
      </div>
    )
  }

  const holdings = live.holdings ?? []
  const summary = latest?.summary ?? {}
  const themes: Record<string, number> = latest?.theme_concentration ?? {}
  const coverage = coverageResp?.coverage ?? []

  const contributors: Contributors =
    contribResp ?? computeContributors(holdings, live.daily_pnl ?? 0, live.total_value ?? 0)

  const missingRatios = coverage.filter((c) => c.has_valuation && !c.has_ratios).length
  const noRag = coverage.filter((c) => c.has_valuation && !c.has_rag).length
  const valRisk = summary.high_valuation_risk_positions ?? 0
  const finnhubConfigured = providers?.finnhub?.configured ?? false

  const mainRisk = mainRiskText(summary, themes)
  const nextAction = nextActionText({ costBasisMissing: !!live.cost_basis_missing, missingRatios, noRag, valRisk, finnhubConfigured })

  const researchItems: { text: string; href: string }[] = []
  if (missingRatios > 0) researchItems.push({ text: `Compute ratios for ${missingRatios} tickers`, href: '/coverage' })
  if (noRag > 0) researchItems.push({ text: `Run RAG/memos for ${noRag} holdings`, href: '/coverage' })
  if (valRisk > 0) researchItems.push({ text: `Review ${valRisk} valuation-risk holdings`, href: '/risk' })

  const liveStream = providers?.live_stream
  const liveMode: LiveMode = liveStream?.available ? 'finnhub_ws' : 'polling_fallback'
  const providerName = finnhubConfigured ? 'finnhub' : 'yfinance'
  const lastUpdated = providers?.finnhub?.last_success_at ?? null

  return (
    <MarketTerminal
      holdings={holdings}
      totalValue={live.total_value ?? 0}
      dailyPnl={live.daily_pnl ?? 0}
      dailyPnlPct={live.daily_pnl_pct ?? 0}
      reports={reportsResp?.reports ?? []}
      providers={providers ?? null}
      contributors={contributors}
      mainRisk={mainRisk}
      nextAction={nextAction}
      liveMode={liveMode}
      providerName={providerName}
      lastUpdated={lastUpdated}
      researchItems={researchItems}
    />
  )
}
