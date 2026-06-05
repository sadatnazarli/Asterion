import { ContributorColumns } from './Contributors'
import { type Contributors } from '@/lib/insights'
import { isNum, money, pct } from '@/lib/format'

// Plain-English "what happened today" box. Sits above the chart, not in a sidebar.
export function TodaysReadout({
  totalValue,
  dailyPnl,
  dailyPnlPct,
  contributors,
  mainRisk,
  nextAction,
}: {
  totalValue: number
  dailyPnl: number
  dailyPnlPct: number
  contributors: Contributors
  mainRisk: string
  nextAction: string
}) {
  const up = dailyPnl >= 0
  const dir = up ? 'up' : 'down'
  const color = up ? 'text-up' : 'text-down'
  const unexplained = contributors.unexplained_difference

  return (
    <section
      className="accent-stripe relative overflow-hidden rounded-md border border-white/[0.06] bg-panel pl-[2px] shadow-elev"
      data-testid="todays-readout"
    >
      <header className="flex items-center justify-between border-b border-white/[0.05] px-3.5 py-2">
        <span className="label text-foreground/90">Today&apos;s portfolio readout</span>
        <span className="text-2xs text-faint">estimated · daily % × position value</span>
      </header>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 px-3.5 py-3.5 md:grid-cols-[1.35fr_1fr]">
        <div className="space-y-3">
          <p className="text-[0.9rem] leading-relaxed text-foreground/90">
            Your portfolio is worth <strong className="num font-semibold text-foreground">{money(totalValue)}</strong> and
            is{' '}
            <strong className={`num font-semibold ${color}`}>
              {dir} {money(Math.abs(dailyPnl))} ({pct(dailyPnlPct, { signed: true })})
            </strong>{' '}
            today.
          </p>
          <div className="space-y-2 text-sm leading-relaxed">
            <p className="flex gap-2">
              <span className="mt-px shrink-0 text-2xs font-semibold uppercase tracking-label text-warn">Main risk</span>
              <span className="text-mutedForeground">{mainRisk}</span>
            </p>
            <p className="flex gap-2">
              <span className="mt-px shrink-0 text-2xs font-semibold uppercase tracking-label text-accent">Next</span>
              <span className="text-mutedForeground">{nextAction}</span>
            </p>
          </div>
        </div>
        <div className="md:border-l md:border-white/[0.05] md:pl-6">
          <ContributorColumns positive={contributors.top_positive} negative={contributors.top_negative} />
          {isNum(unexplained) && Math.abs(unexplained) >= 0.01 && (
            <p className="mt-2.5 text-2xs leading-relaxed text-faint">
              Unexplained vs reported P/L: {money(unexplained).replace('$-', '-$')} (rounding / positions without a live
              quote).
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
