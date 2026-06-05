import LiveMonitorClient from '@/components/LiveMonitorClient'
import { fetchJson } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function LivePage() {
  const tickers = ['MSFT', 'NVDA', 'META', 'PLTR', 'VOO', 'VRT']
  const providers = await fetchJson<any>('/api/system/providers')
  const initialQuotes: Record<string, { price: number; change_pct: number }> = {}
  await Promise.all(
    tickers.map(async (ticker) => {
      const q = await fetchJson<{ c: number; dp?: number }>(`/api/market/quote/${ticker}`)
      if (q?.c) initialQuotes[ticker] = { price: q.c, change_pct: q.dp ?? 0 }
    }),
  )

  return (
    <LiveMonitorClient
      initialQuotes={initialQuotes}
      finnhubConfigured={providers?.finnhub?.configured ?? false}
      setupHint={providers?.finnhub?.setup_hint}
    />
  )
}
