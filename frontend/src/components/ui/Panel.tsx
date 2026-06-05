import { ReactNode } from 'react'

// Terminal module surface. Separation comes from panel fill + a hairline edge,
// not a hard border. Header is a calm uppercase label row. Optional accent
// stripe marks the one primary module on a screen.
export function Panel({
  title,
  right,
  children,
  className = '',
  bodyClassName = '',
  accent = false,
  elevated = false,
  testId,
}: {
  title?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
  accent?: boolean
  elevated?: boolean
  testId?: string
}) {
  return (
    <section
      data-testid={testId}
      className={`relative overflow-hidden rounded-md border border-white/[0.06] ${
        elevated ? 'bg-panel2 shadow-elev' : 'bg-panel shadow-panel'
      } ${accent ? 'accent-stripe' : ''} ${className}`}
    >
      {(title || right) && (
        <header className="flex items-center justify-between border-b border-white/[0.05] px-3 py-2">
          <div className="label">{title}</div>
          {right}
        </header>
      )}
      <div className={bodyClassName || 'p-3'}>{children}</div>
    </section>
  )
}
