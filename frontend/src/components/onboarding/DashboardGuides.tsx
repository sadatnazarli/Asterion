import Link from 'next/link'
import { Panel } from '@/components/ui/Panel'

// "Read this page in this order" — orients a beginner before the numbers.
export function ReadingOrder() {
  const steps = [
    'Look at today’s P/L — did you go up or down, and by how much.',
    'Check who helped and who hurt — which holdings moved you.',
    'Check the biggest risk — the one thing most worth watching.',
    'Check what to do next — research actions, never buy/sell calls.',
  ]
  return (
    <div className="rounded-md border border-white/[0.06] bg-panel px-3.5 py-3" data-testid="reading-order">
      <div className="label mb-2">Read this page in this order</div>
      <ol className="space-y-1.5">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-foreground/90">
            <span className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent/15 text-2xs font-bold text-accent">
              {i + 1}
            </span>
            {s}
          </li>
        ))}
      </ol>
    </div>
  )
}

// Plain-English read of the portfolio, generated from the real numbers.
export function AsterionExplains({
  concentrated,
  coreEtfPct,
  coreBelowTarget,
  topNegative,
  dailyUp,
}: {
  concentrated: boolean
  coreEtfPct: string
  coreBelowTarget: boolean
  topNegative: string[]
  dailyUp: boolean
}) {
  const lines: string[] = []
  lines.push(
    concentrated
      ? 'Your portfolio is not bad, but it is concentrated — a few big positions drive most of the result.'
      : 'Your portfolio is reasonably spread across positions, so no single name dominates.',
  )
  lines.push(
    coreBelowTarget
      ? `Broad index funds (like VOO) protect you, but at ${coreEtfPct} they are slightly below the 30% target.`
      : `Your broad index funds sit at ${coreEtfPct}, at or above the 30% cushion target.`,
  )
  if (topNegative.length) {
    lines.push(`Today’s ${dailyUp ? 'drag' : 'loss'} mostly came from ${topNegative.slice(0, 3).join(', ')}.`)
  }
  lines.push('Do not judge a long-term portfolio by one red day — single days are noise, not the thesis.')

  return (
    <Panel title="Asterion explains" accent testId="asterion-explains">
      <ul className="space-y-2 text-sm leading-relaxed">
        {lines.map((l, i) => (
          <li key={i} className="flex gap-2.5">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <span className="text-foreground/90">{l}</span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

// "What should I do now?" — research actions only, never buy/sell.
export type ChecklistItem = { text: string; href: string }
export function ActionChecklist({ items }: { items: ChecklistItem[] }) {
  return (
    <Panel title="What should I do now?" testId="action-checklist">
      <p className="mb-2 text-2xs text-faint">Research steps only — Asterion never tells you to buy or sell.</p>
      {items.length === 0 ? (
        <div className="text-2xs text-up">Nothing outstanding — your portfolio data is complete.</div>
      ) : (
        <ul className="space-y-1.5">
          {items.map((a, i) => (
            <li key={i}>
              <Link href={a.href} className="flex items-start gap-2.5 text-sm text-foreground/90 transition-colors hover:text-accent">
                <span className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded border border-white/15 text-2xs text-accent">
                  ☐
                </span>
                {a.text}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
