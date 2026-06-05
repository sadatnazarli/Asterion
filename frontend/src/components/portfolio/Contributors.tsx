import Link from 'next/link'
import { type ContribRow } from '@/lib/insights'
import { isNum, money, pct } from '@/lib/format'

function Row({ r }: { r: ContribRow }) {
  const up = r.estimated_contribution_dollars >= 0
  return (
    <Link
      href={`/ticker/${r.ticker}`}
      className="-mx-1 flex items-center justify-between rounded px-1.5 py-1 transition-colors hover:bg-white/[0.04]"
    >
      <span className="num text-xs font-semibold text-foreground">{r.ticker}</span>
      <span className="flex items-center gap-2.5">
        <span className={`num text-2xs ${up ? 'text-up' : 'text-down'}`}>
          {isNum(r.daily_change_pct) ? pct(r.daily_change_pct, { signed: true }) : '—'}
        </span>
        <span className={`num w-14 text-right text-2xs font-semibold tabular-nums ${up ? 'text-up' : 'text-down'}`}>
          {up ? '+' : ''}
          {money(r.estimated_contribution_dollars).replace('$-', '-$')}
        </span>
      </span>
    </Link>
  )
}

export function ContributorColumns({
  positive,
  negative,
}: {
  positive: ContribRow[]
  negative: ContribRow[]
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <div className="mb-1 text-2xs font-semibold uppercase tracking-wider text-up">Helped today</div>
        {positive.length ? positive.map((r) => <Row key={r.ticker} r={r} />) : (
          <div className="px-1 text-2xs text-faint">nothing positive today</div>
        )}
      </div>
      <div>
        <div className="mb-1 text-2xs font-semibold uppercase tracking-wider text-down">Hurt today</div>
        {negative.length ? negative.map((r) => <Row key={r.ticker} r={r} />) : (
          <div className="px-1 text-2xs text-faint">nothing negative today</div>
        )}
      </div>
    </div>
  )
}
