'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

const KEY = 'asterion-onboarded'
export const OPEN_GUIDE_EVENT = 'asterion:open-guide'

type Step = { page: string; href: string; title: string; body: string }
const STEPS: Step[] = [
  { page: 'Dashboard', href: '/dashboard', title: 'Start here', body: 'A plain-English summary of what happened to your portfolio today — read it top to bottom.' },
  { page: 'Market', href: '/market', title: 'Live market context', body: 'See whether the whole market is moving or only your holdings, with a live chart and heatmap.' },
  { page: 'Portfolio', href: '/portfolio', title: 'Where your money is', body: 'Every position you hold, what it is worth, and how much of your portfolio it makes up.' },
  { page: 'Risk', href: '/risk', title: 'What can hurt you', body: 'Concentration, theme, valuation and data risks — graded low / medium / high in plain language.' },
  { page: 'Ticker', href: '/ticker/PLTR', title: 'Deep research', body: 'Open any company to judge whether it looks strong, risky, or overpriced. Never a buy/sell call.' },
]

export function OnboardingModal() {
  const [open, setOpen] = useState(false)
  const [i, setI] = useState(0)

  useEffect(() => {
    try {
      if (!window.localStorage.getItem(KEY)) setOpen(true)
    } catch {}
    const handler = () => {
      setI(0)
      setOpen(true)
    }
    window.addEventListener(OPEN_GUIDE_EVENT, handler)
    return () => window.removeEventListener(OPEN_GUIDE_EVENT, handler)
  }, [])

  const dismiss = () => {
    try {
      window.localStorage.setItem(KEY, '1')
    } catch {}
    setOpen(false)
  }

  if (!open) return null
  const step = STEPS[i]
  const last = i === STEPS.length - 1

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      data-testid="onboarding-modal"
      role="dialog"
      aria-modal="true"
    >
      <div className="mx-4 w-full max-w-md overflow-hidden rounded-lg border border-white/10 bg-panel2 shadow-elev">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
          <span className="label text-foreground/90">Welcome to Asterion · {i + 1} of {STEPS.length}</span>
          <button
            onClick={dismiss}
            data-testid="onboarding-dismiss"
            aria-label="Close walkthrough"
            className="text-mutedForeground transition-colors hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <div className="px-4 py-4">
          <div className="mb-1 flex items-baseline gap-2">
            <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-label text-accent">
              {step.page}
            </span>
            <h3 className="text-base font-bold tracking-tight">{step.title}</h3>
          </div>
          <p className="text-sm leading-relaxed text-mutedForeground">{step.body}</p>
          <Link href={step.href} onClick={dismiss} className="mt-2 inline-block text-2xs text-accent hover:underline">
            Open {step.page} →
          </Link>

          {/* progress dots */}
          <div className="mt-4 flex items-center gap-1.5">
            {STEPS.map((_, k) => (
              <span key={k} className={`h-1.5 rounded-full transition-all ${k === i ? 'w-5 bg-accent' : 'w-1.5 bg-white/15'}`} />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-white/[0.06] px-4 py-2.5">
          <button onClick={dismiss} className="text-2xs text-faint transition-colors hover:text-mutedForeground">
            Skip
          </button>
          <div className="flex items-center gap-1.5">
            {i > 0 && (
              <button
                onClick={() => setI((v) => v - 1)}
                className="rounded border border-white/[0.08] px-3 py-1 text-2xs font-semibold text-mutedForeground transition-colors hover:text-foreground"
              >
                Back
              </button>
            )}
            <button
              onClick={() => (last ? dismiss() : setI((v) => v + 1))}
              className="rounded bg-accent/90 px-3 py-1 text-2xs font-semibold text-white transition-colors hover:bg-accent"
            >
              {last ? 'Done' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Header button that re-opens the walkthrough.
export function GuideButton() {
  return (
    <button
      onClick={() => window.dispatchEvent(new Event(OPEN_GUIDE_EVENT))}
      data-testid="guide-button"
      className="rounded border border-white/[0.08] px-2 py-1 text-2xs font-medium text-mutedForeground transition-colors hover:border-accent/50 hover:text-foreground"
      title="Replay the guided walkthrough"
    >
      Guide
    </button>
  )
}
