import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { DataQualityBadge } from '@/components/ui/Badges'
import { ErrorBanner } from '@/components/ui/States'
import { BeginnerOnly } from '@/components/ui/ViewMode'
import { HelpBox } from '@/components/onboarding/HelpBox'
import { HelpTip } from '@/components/ui/HelpTip'
import { define } from '@/lib/glossary'
import { fetchJson, getApiBase } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Cov = {
  ticker: string
  asset_type: string
  has_price: boolean
  has_cik: boolean
  has_facts: boolean
  has_ratios: boolean
  has_valuation: boolean
  has_rag: boolean
  has_memo: boolean
  data_quality: string
}

function Cell({ ok }: { ok: boolean }) {
  return <span className={ok ? 'text-up' : 'text-faint'}>{ok ? '●' : '○'}</span>
}

export default async function CoveragePage() {
  const data = await fetchJson<{ coverage: Cov[] }>('/api/portfolio/coverage')

  if (!data?.coverage) {
    return (
      <div className="p-3">
        <ErrorBanner title="Coverage unavailable" detail={`No data from ${getApiBase()}/api/portfolio/coverage.`} />
      </div>
    )
  }

  const cols: { key: keyof Cov; label: string; help?: string }[] = [
    { key: 'has_price', label: 'Price' },
    { key: 'has_cik', label: 'CIK', help: define('cik') },
    { key: 'has_facts', label: 'Facts', help: define('sec facts') },
    { key: 'has_ratios', label: 'Ratios' },
    { key: 'has_valuation', label: 'Valuation', help: define('valuation risk') },
    { key: 'has_rag', label: 'RAG', help: define('rag') },
    { key: 'has_memo', label: 'Memo', help: define('memo') },
  ]

  return (
    <div className="space-y-4 px-4 py-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Coverage Matrix</h1>
        <p className="mt-0.5 text-xs text-mutedForeground">
          What data each holding has across the pipeline. <span className="text-up">●</span> present ·{' '}
          <span className="text-faint">○</span> missing.
        </p>
      </div>

      <BeginnerOnly>
        <HelpBox answers="How complete is Asterion’s data on each holding?">
          A filled dot means that piece of data is present. Hover any column’s “?” to learn what it is.
        </HelpBox>
      </BeginnerOnly>

      <Panel bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-2xs uppercase tracking-wider text-mutedForeground">
                <th className="px-3 py-2 text-left">Ticker</th>
                {cols.map((c) => (
                  <th key={c.key} className="px-3 py-2 text-center">
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {c.help && <HelpTip text={c.help} label={c.label} />}
                    </span>
                  </th>
                ))}
                <th className="px-3 py-2 text-left">Quality</th>
              </tr>
            </thead>
            <tbody>
              {data.coverage.map((c) => (
                <tr key={c.ticker} className="border-b border-white/[0.035] transition-colors last:border-0 hover:bg-white/[0.025]">
                  <td className="px-3 py-2">
                    <Link href={`/ticker/${c.ticker}`} className="num font-semibold hover:text-accent">{c.ticker}</Link>
                    <span className="ml-2 text-2xs text-faint">{c.asset_type}</span>
                  </td>
                  {cols.map((col) => (
                    <td key={col.key} className="px-3 py-2 text-center">
                      <Cell ok={Boolean(c[col.key])} />
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <DataQualityBadge quality={c.data_quality} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
