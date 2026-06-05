import { isNum, pctFrac } from '@/lib/format'

export type ContribRow = {
  ticker: string
  current_value: number
  daily_change_pct: number
  estimated_contribution_dollars: number
  direction: 'up' | 'down' | 'flat'
  theme?: string | null
}

export type Contributors = {
  total_value: number
  daily_pnl_reported: number
  sum_contributions: number
  unexplained_difference: number
  top_positive: ContribRow[]
  top_negative: ContribRow[]
  all: ContribRow[]
}

// Frontend fallback mirroring the backend /portfolio/contributors math, so the
// readout still works if the endpoint is unavailable (older backend / 404).
export function computeContributors(
  holdings: { ticker: string; current_value: number; daily_change_pct?: number | null; theme?: string | null }[],
  dailyPnlReported: number,
  totalValue: number,
): Contributors {
  const rows: ContribRow[] = holdings.map((h) => {
    const val = isNum(h.current_value) ? h.current_value : 0
    const dp = isNum(h.daily_change_pct) ? (h.daily_change_pct as number) : 0
    const contrib = val * (dp / 100)
    return {
      ticker: h.ticker,
      current_value: val,
      daily_change_pct: dp,
      estimated_contribution_dollars: contrib,
      direction: contrib > 0 ? 'up' : contrib < 0 ? 'down' : 'flat',
      theme: h.theme ?? null,
    }
  })
  rows.sort((a, b) => b.estimated_contribution_dollars - a.estimated_contribution_dollars)
  const positive = rows.filter((r) => r.estimated_contribution_dollars > 0)
  const negative = rows.filter((r) => r.estimated_contribution_dollars < 0)
  const sum = rows.reduce((s, r) => s + r.estimated_contribution_dollars, 0)
  return {
    total_value: totalValue,
    daily_pnl_reported: dailyPnlReported,
    sum_contributions: sum,
    unexplained_difference: dailyPnlReported - sum,
    top_positive: positive.slice(0, 3),
    top_negative: [...negative].reverse().slice(0, 3),
    all: rows,
  }
}

export function mainRiskText(summary: {
  core_etf_exposure?: number
  speculative_exposure?: number
  high_valuation_risk_positions?: number
}, themes: Record<string, number>): string {
  const ai = (themes['AI/semiconductor'] ?? 0) + (themes['AI/software'] ?? 0) + (themes['data center infrastructure'] ?? 0)
  const core = summary.core_etf_exposure ?? 0
  const valRisk = summary.high_valuation_risk_positions ?? 0
  const parts: string[] = []
  if (ai > 0.3) parts.push(`AI/semiconductor exposure (${pctFrac(ai, { decimals: 0 })})`)
  if (valRisk > 0) parts.push(`${valRisk} high-valuation holdings`)
  if (core < 0.3) parts.push(`thin broad-ETF protection (${pctFrac(core, { decimals: 0 })})`)
  if (parts.length === 0) return 'No single concentration dominates — risk is reasonably spread.'
  return `${parts.join(' and ')} are driving most of the volatility.`
}

export function nextActionText(opts: {
  costBasisMissing: boolean
  missingRatios: number
  noRag: number
  valRisk: number
  finnhubConfigured: boolean
}): string {
  const a: string[] = []
  if (opts.costBasisMissing) a.push('add cost basis')
  if (opts.missingRatios > 0) a.push(`complete ratios for ${opts.missingRatios} tickers`)
  if (opts.noRag > 0) a.push('run missing RAG/memos')
  if (opts.valRisk > 0) a.push(`review ${opts.valRisk} valuation-risk holdings`)
  if (!opts.finnhubConfigured) a.push('add a Finnhub key for live data')
  if (a.length === 0) return 'No outstanding data or policy actions.'
  return `${a.join(', ')}.`
}
