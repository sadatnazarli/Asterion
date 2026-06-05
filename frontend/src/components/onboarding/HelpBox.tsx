import { type ReactNode } from 'react'

// Beginner page-help box: states the single question this page answers, in plain
// language. Presentational only — gate it with <BeginnerOnly> at the call site.
export function HelpBox({ answers, children }: { answers: string; children?: ReactNode }) {
  return (
    <div
      className="accent-stripe flex items-start gap-2.5 rounded-md border border-white/[0.06] bg-panel pl-3.5 pr-3 py-2.5"
      data-testid="help-box"
    >
      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-accent/40 text-[0.6rem] font-bold text-accent">
        i
      </span>
      <div className="text-sm leading-relaxed">
        <span className="text-mutedForeground">This page answers: </span>
        <span className="font-semibold text-foreground">{answers}</span>
        {children && <div className="mt-1 text-2xs leading-relaxed text-mutedForeground">{children}</div>}
      </div>
    </div>
  )
}
