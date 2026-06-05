import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { fetchJson } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Report = { name: string; type: string; size_bytes: number }

function ReportRow({ r }: { r: Report }) {
  return (
    <Link
      href={`/reports/${encodeURIComponent(r.name)}`}
      className="flex items-center justify-between border-b border-border/50 px-3 py-2 last:border-0 hover:bg-panel2"
    >
      <span className="num truncate pr-3 text-sm text-accent">{r.name}</span>
      <span className="flex shrink-0 items-center gap-2 text-2xs text-mutedForeground">
        <span>{(r.size_bytes / 1024).toFixed(1)} KB</span>
        <span className="rounded border border-border bg-panel2 px-1.5 py-0.5 uppercase tracking-wide">{r.type}</span>
      </span>
    </Link>
  )
}

export default async function ReportsPage() {
  const data = await fetchJson<{ reports: Report[] }>('/api/reports')
  const reports = data?.reports ?? []
  const portfolio = reports.filter((r) => /portfolio|coverage/.test(r.name))
  const tickers = reports.filter((r) => !/portfolio|coverage/.test(r.name))

  return (
    <div className="space-y-3 p-3">
      <div className="border-b border-border pb-2">
        <h1 className="text-lg font-bold tracking-tight">Research Reports</h1>
        <p className="text-2xs text-mutedForeground">Generated JSON scorecards and Markdown memos.</p>
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title="Portfolio intelligence" bodyClassName="p-0">
          {portfolio.length ? portfolio.map((r) => <ReportRow key={r.name} r={r} />) : (
            <div className="px-3 py-4 text-2xs text-faint">none generated</div>
          )}
        </Panel>
        <Panel title="Ticker scorecards" bodyClassName="p-0">
          {tickers.length ? tickers.map((r) => <ReportRow key={r.name} r={r} />) : (
            <div className="px-3 py-4 text-2xs text-faint">none generated</div>
          )}
        </Panel>
      </div>
    </div>
  )
}
