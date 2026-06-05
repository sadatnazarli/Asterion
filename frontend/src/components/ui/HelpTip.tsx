'use client'

import { useId, useState, type ReactNode } from 'react'
import { define } from '@/lib/glossary'

// Small "?" help icon with a hover/focus tooltip. Works on hover and on
// keyboard focus / tap (click toggles). Used for every technical term.
export function HelpTip({ text, label, className = '' }: { text: string; label?: string; className?: string }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <span className={`relative inline-flex ${className}`}>
      <button
        type="button"
        aria-label={label ? `What does ${label} mean?` : 'Explain this'}
        aria-describedby={id}
        data-testid="help-tip"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-white/15 text-[0.6rem] font-bold leading-none text-mutedForeground transition-colors hover:border-accent/60 hover:text-accent"
      >
        ?
      </button>
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute left-1/2 top-5 z-50 w-56 -translate-x-1/2 rounded-md border border-white/10 bg-panel3 px-2.5 py-2 text-2xs leading-relaxed text-foreground shadow-elev transition-opacity ${
          open ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {label && <span className="mb-0.5 block font-semibold uppercase tracking-label text-mutedForeground">{label}</span>}
        {text}
      </span>
    </span>
  )
}

// Inline glossary term: renders the label with a dotted underline + a HelpTip
// resolved from the central glossary (or an explicit `def`).
export function Term({ children, term, def }: { children: ReactNode; term?: string; def?: string }) {
  const key = term ?? (typeof children === 'string' ? children : '')
  const text = def ?? define(key) ?? ''
  return (
    <span className="inline-flex items-center gap-1">
      <span className="underline decoration-dotted decoration-white/30 underline-offset-2">{children}</span>
      {text && <HelpTip text={text} label={key} />}
    </span>
  )
}
