import { PortfolioTable, type Holding } from '@/components/portfolio/PortfolioTable'
import { MetricTile } from '@/components/ui/MetricTile'
import { Panel } from '@/components/ui/Panel'
import { HBarList } from '@/components/portfolio/HBar'
import { ErrorBanner } from '@/components/ui/States'
import { BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { fetchJson, getApiBase } from '@/lib/api'
import { compactMoney, money, pct } from '@/lib/format'

export const dynamic = 'force-dynamic'

export default async function PortfolioPage() {
  const [live, coverage] = await Promise.all([
    fetchJson<any>('/api/portfolio/live'),
    fetchJson<{ coverage: { ticker: string; data_quality: string }[] }>('/api/portfolio/coverage'),
  ])

  if (!live) {
    return (
      <div className="p-3">
        <ErrorBanner title="Portfolio needs the backend" detail={`No data from ${getApiBase()}/api/portfolio/live.`} />
      </div>
    )
  }

  const holdings: Holding[] = live.holdings ?? []
  const coverageMap: Record<string, string> = Object.fromEntries(
    (coverage?.coverage ?? []).map((c) => [c.ticker, c.data_quality]),
  )

  const top = [...holdings]
    .sort((a, b) => b.current_value - a.current_value)
    .slice(0, 8)
    .map((h) => ({ label: h.ticker, value: h.current_value, valueText: compactMoney(h.current_value) }))

  return (
    <div className="space-y-4 px-4 py-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Holdings &amp; Performance</h1>
        <p className="mt-0.5 text-xs text-mutedForeground">Live values, weights, and data quality per position. Click a row to research.</p>
      </div>

      <BeginnerOnly>
        <HelpBox answers="Where is my money?">
          Each row is one position. “Value” is what it’s worth now; “Weight” is how big a slice of your portfolio it is.
        </HelpBox>
      </BeginnerOnly>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile label="Total value" value={money(live.total_value)} />
        <MetricTile
          label="Today P/L"
          value={`${live.daily_pnl >= 0 ? '+' : ''}${money(live.daily_pnl).replace('$-', '-$')}`}
          sub={pct(live.daily_pnl_pct, { signed: true })}
          tone={live.daily_pnl >= 0 ? 'up' : 'down'}
        />
        <MetricTile
          label="Total P/L"
          value={live.total_pnl != null ? money(live.total_pnl) : '—'}
          missingReason="no cost basis"
          help="What you originally paid for a position; without it, only today’s move can be shown, not total profit."
          explain="Add what you paid (cost basis) to unlock lifetime profit/loss — today only shows the day’s move."
        />
        <MetricTile label="Positions" value={String(holdings.length)} />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_300px]">
        <PortfolioTable holdings={holdings} coverageMap={coverageMap} costBasisMissing={!!live.cost_basis_missing} />
        <Panel title="Concentration — top 8">
          <HBarList rows={top} tone="accent" linkBase="/ticker/" />
        </Panel>
      </div>
    </div>
  )
}
