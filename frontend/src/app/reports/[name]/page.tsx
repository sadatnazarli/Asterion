import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'
import { EmptyState } from '@/components/ui/States'
import { fetchJson } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function ReportViewer({ params }: { params: Promise<{ name: string }> }) {
  const { name } = await params
  const data = await fetchJson<any>(`/api/reports/${encodeURIComponent(name)}`)
  const isMarkdown = name.endsWith('.md')

  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <h1 className="num text-base font-bold tracking-tight">{name}</h1>
        <Link href="/reports" className="rounded border border-border px-2 py-1 text-2xs text-mutedForeground hover:text-foreground">
          ← Reports
        </Link>
      </div>
      <Panel bodyClassName="p-0">
        {!data ? (
          <EmptyState title="Report not found" />
        ) : isMarkdown ? (
          <pre className="num whitespace-pre-wrap p-4 text-sm leading-relaxed text-foreground">{data.content}</pre>
        ) : (
          <pre className="num overflow-x-auto p-4 text-xs leading-relaxed text-up">{JSON.stringify(data, null, 2)}</pre>
        )}
      </Panel>
    </div>
  )
}
