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

// Single shimmer block — the primitive every skeleton is built from.
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export function LoadingSkeleton({ rows = 3, className = '' }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  )
}

export function ChartLoading({ height = 420 }: { height?: number }) {
  return (
    <div className="relative w-full overflow-hidden rounded-md bg-panel2" style={{ height }}>
      <div className="terminal-grid absolute inset-0" />
      <div className="skeleton absolute inset-0 opacity-60" />
      <div className="absolute inset-0 flex items-center justify-center text-2xs text-faint">
        loading chart…
      </div>
    </div>
  )
}

// Full-page skeleton matching the terminal layout: header row, a metric-tile
// grid, and two content panels. Reused by every route's loading.tsx so category
// switches paint an instant, on-brand frame while data streams in.
export function PageSkeleton({ tiles = 4, panels = 2 }: { tiles?: number; panels?: number }) {
  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: tiles }).map((_, i) => (
          <div key={i} className="rounded-md border border-white/[0.05] bg-panel px-3 py-2.5">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-2.5 h-6 w-24" />
            <Skeleton className="mt-2 h-2.5 w-20" />
          </div>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {Array.from({ length: panels }).map((_, i) => (
          <div key={i} className="overflow-hidden rounded-md border border-white/[0.06] bg-panel shadow-panel">
            <div className="border-b border-white/[0.05] px-3 py-2">
              <Skeleton className="h-3 w-28" />
            </div>
            <div className="space-y-2.5 p-3">
              {Array.from({ length: 5 }).map((_, r) => (
                <div key={r} className="flex items-center gap-3">
                  <Skeleton className="h-3.5 w-3.5 rounded-full" />
                  <Skeleton className="h-3.5 flex-1" />
                  <Skeleton className="h-3.5 w-16" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
