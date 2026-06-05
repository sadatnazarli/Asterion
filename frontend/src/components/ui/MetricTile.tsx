import { ReactNode } from 'react'
import { HelpTip } from './HelpTip'
import { BeginnerOnly } from './ViewMode'

// One metric: small calm label, big mono value, optional sub-line.
// When value is missing, shows an explicit reason instead of a bare N/A.
// M8.11: optional `help` (?-tooltip, both modes) and `explain` (beginner-only
// plain-English sentence) make every metric self-describing.
export function MetricTile({
  label,
  value,
  sub,
  missingReason,
  tone = 'default',
  help,
  explain,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  missingReason?: string
  tone?: 'default' | 'up' | 'down' | 'warn'
  help?: string
  explain?: string
}) {
  const isMissing = value === '—' || value === null || value === undefined
  const toneColor =
    tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : tone === 'warn' ? 'text-warn' : 'text-foreground'

  return (
    <div className="rounded-md border border-white/[0.05] bg-panel px-3 py-2.5 transition-colors hover:bg-panel2">
      <div className="flex items-center gap-1">
        <span className="label">{label}</span>
        {help && <HelpTip text={help} label={label} />}
      </div>
      {isMissing ? (
        <div className="mt-1.5 text-sm text-faint" title={missingReason}>
          {missingReason ? `unavailable · ${missingReason}` : 'unavailable'}
        </div>
      ) : (
        <div className={`num mt-1.5 text-xl font-semibold tracking-tight ${toneColor}`}>{value}</div>
      )}
      {sub && !isMissing && <div className="mt-1 text-2xs text-mutedForeground">{sub}</div>}
      {explain && (
        <BeginnerOnly>
          <div className="mt-1.5 text-2xs leading-relaxed text-faint">{explain}</div>
        </BeginnerOnly>
      )}
    </div>
  )
}
