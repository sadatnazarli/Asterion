import Link from 'next/link'
import { isNum } from '@/lib/format'

// Dependency-free horizontal bar row. Label left, value right, filled track.
export function HBarList({
  rows,
  max,
  tone = 'accent',
  linkBase,
}: {
  rows: { label: string; value: number; valueText: string }[]
  max?: number
  tone?: 'accent' | 'up' | 'warn'
  linkBase?: string // e.g. "/ticker/" -> row label becomes a link
}) {
  const peak = max ?? Math.max(...rows.map((r) => (isNum(r.value) ? r.value : 0)), 1)
  const bar = tone === 'up' ? 'bg-up/85' : tone === 'warn' ? 'bg-warn/85' : 'bg-accent/85'
  return (
    <div className="space-y-2">
      {rows.map((r) => {
        const w = Math.max(2, Math.min(100, (r.value / peak) * 100))
        const Label = linkBase ? (
          <Link href={`${linkBase}${encodeURIComponent(r.label)}`} className="transition-colors hover:text-accent">
            {r.label}
          </Link>
        ) : (
          r.label
        )
        return (
          <div key={r.label} className="flex items-center gap-2.5">
            <div className="num w-20 shrink-0 text-2xs font-medium text-foreground">{Label}</div>
            <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div className={`absolute inset-y-0 left-0 rounded-full ${bar}`} style={{ width: `${w}%` }} />
            </div>
            <div className="num w-16 shrink-0 text-right text-2xs tabular-nums text-mutedForeground">{r.valueText}</div>
          </div>
        )
      })}
    </div>
  )
}
