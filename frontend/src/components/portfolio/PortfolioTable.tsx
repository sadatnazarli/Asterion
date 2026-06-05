'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DataQualityBadge } from '@/components/ui/Badges'
import { HelpTip } from '@/components/ui/HelpTip'
import { define } from '@/lib/glossary'
import { compactMoney, isNum, money, pct, pctFrac } from '@/lib/format'

export type Holding = {
  ticker: string
  asset_type?: string | null
  theme?: string | null
  current_value: number
  current_price?: number | null
  daily_change_pct?: number | null
  weight?: number
  value_source?: string | null
  risk_label?: string | null
}

type SortKey = 'ticker' | 'current_value' | 'weight' | 'current_price' | 'daily_change_pct'

export function PortfolioTable({
  holdings,
  coverageMap,
  costBasisMissing,
}: {
  holdings: Holding[]
  coverageMap: Record<string, string>
  costBasisMissing: boolean
}) {
  const router = useRouter()
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<SortKey>('current_value')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')

  const rows = useMemo(() => {
    const filtered = holdings.filter(
      (h) =>
        h.ticker.toLowerCase().includes(q.toLowerCase()) ||
        (h.theme ?? '').toLowerCase().includes(q.toLowerCase()),
    )
    return filtered.sort((a, b) => {
      const av = a[sort] as number | string
      const bv = b[sort] as number | string
      let c = 0
      if (typeof av === 'string' || typeof bv === 'string') c = String(av).localeCompare(String(bv))
      else c = (av as number) - (bv as number)
      return dir === 'asc' ? c : -c
    })
  }, [holdings, q, sort, dir])

  const setSortKey = (k: SortKey) => {
    if (k === sort) setDir(dir === 'asc' ? 'desc' : 'asc')
    else {
      setSort(k)
      setDir(k === 'ticker' ? 'asc' : 'desc')
    }
  }

  const Th = ({ k, label, align = 'left', help }: { k: SortKey; label: string; align?: 'left' | 'right'; help?: string }) => (
    <th
      className={`select-none px-3 py-2.5 text-2xs font-semibold uppercase tracking-label text-mutedForeground ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
    >
      <span className={`inline-flex items-center gap-1 ${align === 'right' ? 'flex-row-reverse' : ''}`}>
        <span className="cursor-pointer transition-colors hover:text-foreground" onClick={() => setSortKey(k)}>
          {label}
          {sort === k && <span className="ml-1 text-accent">{dir === 'asc' ? '▲' : '▼'}</span>}
        </span>
        {help && <HelpTip text={help} label={label} />}
      </span>
    </th>
  )

  return (
    <div className="overflow-hidden rounded-md border border-white/[0.06] bg-panel shadow-panel">
      <div className="flex items-center justify-between border-b border-white/[0.05] px-3 py-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter ticker / theme…"
          className="h-7 w-52 rounded border border-white/[0.07] bg-panel2 px-2.5 text-xs text-foreground placeholder:text-faint focus:border-accent/60 focus:outline-none"
        />
        <span className="text-2xs text-mutedForeground">{rows.length} positions</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-panel2/95 backdrop-blur supports-[backdrop-filter]:bg-panel2/80">
            <tr className="border-b border-white/[0.06]">
              <Th k="ticker" label="Ticker" />
              <th className="px-3 py-2.5 text-left text-2xs font-semibold uppercase tracking-label text-mutedForeground">Type / Theme</th>
              <Th k="current_value" label="Value" align="right" help={define('current value')} />
              <Th k="weight" label="Weight" align="right" help={define('weight')} />
              <Th k="current_price" label="Price" align="right" />
              <Th k="daily_change_pct" label="Today" align="right" help={define('daily contribution')} />
              <th className="px-3 py-2.5 text-left text-2xs font-semibold uppercase tracking-label text-mutedForeground">
                <span className="inline-flex items-center gap-1">Data <HelpTip text={define('data quality') ?? ''} label="data quality" /></span>
              </th>
              <th className="px-3 py-2.5 text-left text-2xs font-semibold uppercase tracking-label text-mutedForeground">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((h) => {
              const dp = h.daily_change_pct
              const dpColor = !isNum(dp) ? 'text-mutedForeground' : dp! >= 0 ? 'text-up' : 'text-down'
              return (
                <tr
                  key={h.ticker}
                  onClick={() => router.push(`/ticker/${h.ticker}`)}
                  className="group cursor-pointer border-b border-white/[0.035] transition-colors last:border-0 hover:bg-white/[0.025]"
                >
                  <td className="num px-3 py-2.5 font-semibold text-foreground">
                    {h.ticker}
                    {h.risk_label && <span className="ml-1.5 text-2xs text-down">●</span>}
                  </td>
                  <td className="px-3 py-2.5 text-2xs text-mutedForeground">
                    {h.asset_type ?? '—'}
                    {h.theme && <span className="ml-1 text-faint">· {h.theme}</span>}
                  </td>
                  <td className="num px-3 py-2.5 text-right tabular-nums">{money(h.current_value)}</td>
                  <td className="num px-3 py-2.5 text-right tabular-nums text-mutedForeground">{isNum(h.weight) ? pctFrac(h.weight) : '—'}</td>
                  <td className="num px-3 py-2.5 text-right tabular-nums">{isNum(h.current_price) ? money(h.current_price) : '—'}</td>
                  <td className={`num px-3 py-2.5 text-right tabular-nums ${dpColor}`}>{isNum(dp) ? pct(dp, { signed: true }) : '—'}</td>
                  <td className="px-3 py-2.5">
                    <DataQualityBadge quality={coverageMap[h.ticker]} />
                  </td>
                  <td className="px-3 py-2.5 text-2xs text-faint">
                    {h.value_source === 'current_value_optional' ? 'value only' : h.value_source ?? '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {costBasisMissing && (
        <div className="border-t border-white/[0.05] bg-warn/[0.06] px-3 py-2 text-2xs text-warn">
          Cost basis missing for all positions — total P/L cannot be computed. Add share counts to enable realized P/L.
        </div>
      )}
    </div>
  )
}
