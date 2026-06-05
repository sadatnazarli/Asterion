import { ReactNode } from 'react'

export function EmptyState({
  title,
  hint,
  icon,
}: {
  title: string
  hint?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
      <div className="text-2xl opacity-40">{icon ?? '◌'}</div>
      <div className="text-sm font-medium text-mutedForeground">{title}</div>
      {hint && <div className="max-w-md text-2xs text-faint">{hint}</div>}
    </div>
  )
}

export function ErrorBanner({ title, detail }: { title: string; detail?: ReactNode }) {
  return (
    <div className="border border-down/30 bg-down/10 px-3 py-2 text-sm text-down">
      <div className="font-semibold">{title}</div>
      {detail && <div className="mt-0.5 text-2xs text-down/80">{detail}</div>}
    </div>
  )
}

export function LoadingSkeleton({ rows = 3, className = '' }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 w-full animate-pulse rounded bg-panel2" />
      ))}
    </div>
  )
}

export function ChartLoading({ height = 420 }: { height?: number }) {
  return (
    <div className="relative w-full overflow-hidden bg-panel2" style={{ height }}>
      <div className="terminal-grid absolute inset-0" />
      <div className="absolute inset-0 flex items-center justify-center text-2xs text-faint">
        loading chart…
      </div>
    </div>
  )
}
