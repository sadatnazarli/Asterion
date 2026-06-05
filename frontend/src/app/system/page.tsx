import { Panel } from '@/components/ui/Panel'
import { ErrorBanner } from '@/components/ui/States'
import { fetchJson, getApiBase } from '@/lib/api'
import { timeAgo } from '@/lib/format'

export const dynamic = 'force-dynamic'

type Provider = {
  configured?: boolean
  status?: string
  masked_key?: string | null
  last_success_at?: string | null
  env_variables?: string[]
  setup_hint?: string | null
  note?: string
  streaming?: boolean
}

function StatusDot({ ok, fallback }: { ok: boolean; fallback?: boolean }) {
  const cls = ok ? 'bg-up' : fallback ? 'bg-warn' : 'bg-faint'
  return <span className={`inline-block h-2 w-2 rounded-full ${cls}`} />
}

export default async function SystemPage() {
  const providers = await fetchJson<Record<string, Provider>>('/api/system/providers')

  if (!providers) {
    return (
      <div className="p-3">
        <ErrorBanner title="Provider status unavailable" detail={`No response from ${getApiBase()}/api/system/providers.`} />
      </div>
    )
  }

  const liveStream = (providers as any).live_stream as { available?: boolean; mode?: string; endpoint?: string } | undefined
  const rows = Object.entries(providers).filter(([k]) =>
    ['finnhub', 'fmp', 'fred', 'polygon', 'openfigi', 'yfinance'].includes(k),
  )

  return (
    <div className="space-y-4 px-4 py-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">System · Data Providers</h1>
        <p className="mt-0.5 text-xs text-mutedForeground">
          Configuration and live status. Keys are never shown — only a masked suffix. Backend reads both{' '}
          <code className="text-faint">NAME</code> and <code className="text-faint">ASTERION_NAME</code> env forms.
        </p>
      </div>

      {liveStream && (
        <Panel title="Live quote stream">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="flex items-center gap-2">
              <StatusDot ok={!!liveStream.available} fallback />
              <span className="font-medium">
                {liveStream.available ? 'Finnhub WebSocket' : 'Polling fallback (yfinance, delayed)'}
              </span>
            </span>
            <span className="text-2xs text-mutedForeground">mode: {liveStream.mode}</span>
            <span className="num text-2xs text-faint">{liveStream.endpoint}</span>
          </div>
          <p className="mt-2 text-2xs text-faint">
            “Live” means a Finnhub WebSocket is actually streaming. Without a Finnhub key the app polls quotes on a timer
            and labels them as polling — it does not claim real-time.
          </p>
        </Panel>
      )}

      <Panel title="Providers" bodyClassName="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-2xs uppercase tracking-wider text-mutedForeground">
              <th className="px-3 py-2 text-left">Provider</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Key</th>
              <th className="px-3 py-2 text-left">Last success</th>
              <th className="px-3 py-2 text-left">Env vars / hint</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([name, p]) => {
              const ok = !!p.configured
              const fallback = p.status === 'fallback'
              return (
                <tr key={name} className="border-b border-border/60 last:border-0">
                  <td className="px-3 py-2 font-semibold capitalize">{name}</td>
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-2">
                      <StatusDot ok={ok} fallback={fallback} />
                      <span className={ok ? 'text-up' : fallback ? 'text-warn' : 'text-faint'}>
                        {p.status ?? (ok ? 'ok' : 'not configured')}
                      </span>
                    </span>
                  </td>
                  <td className="num px-3 py-2 text-mutedForeground">{p.masked_key ?? '—'}</td>
                  <td className="px-3 py-2 text-2xs text-mutedForeground">
                    {p.last_success_at ? timeAgo(p.last_success_at) : p.note ? p.note : '—'}
                  </td>
                  <td className="px-3 py-2 text-2xs text-faint">
                    {ok ? (p.env_variables?.join(' / ') ?? '') : (p.setup_hint ?? p.env_variables?.join(' / ') ?? '')}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Panel>

      <p className="text-2xs text-faint">
        If a key is set but a provider still reads inactive: env file not loaded by the backend process, a 401 from the
        provider, a rate limit, or the market being closed. Check <code>{getApiBase()}/api/system/env-diagnostics</code>.
      </p>
    </div>
  )
}
