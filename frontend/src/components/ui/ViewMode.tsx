'use client'

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'

export type ViewMode = 'simple' | 'terminal'
const KEY = 'asterion-view-mode'

const Ctx = createContext<{ mode: ViewMode; setMode: (m: ViewMode) => void }>({
  mode: 'simple',
  setMode: () => {},
})

// M8.11: Beginner mode ('simple') is the default everywhere until the user opts
// into Pro ('terminal'). Pro keeps the dense terminal UI; Beginner adds the
// guided explanation layer and hides high-density panels.
function routeDefault(_pathname: string | null): ViewMode {
  return 'simple'
}

export function ModeProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [explicit, setExplicit] = useState<ViewMode | null>(null)

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? window.localStorage.getItem(KEY) : null
    if (stored === 'simple' || stored === 'terminal') setExplicit(stored)
  }, [])

  const mode = explicit ?? routeDefault(pathname)
  const value = useMemo(
    () => ({
      mode,
      setMode: (m: ViewMode) => {
        setExplicit(m)
        try {
          window.localStorage.setItem(KEY, m)
        } catch {}
      },
    }),
    [mode],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useViewMode() {
  return useContext(Ctx)
}

// Beginner ('simple') / Pro ('terminal') labels over the underlying view mode.
const MODE_LABEL: Record<ViewMode, string> = { simple: 'Beginner', terminal: 'Pro' }

export function ModeToggle() {
  const { mode, setMode } = useViewMode()
  return (
    <div
      className="inline-flex items-center gap-0.5 rounded-md border border-white/[0.06] bg-panel2 p-0.5"
      data-testid="mode-toggle"
    >
      {(['simple', 'terminal'] as ViewMode[]).map((m) => (
        <button
          key={m}
          onClick={() => setMode(m)}
          className={`rounded px-2.5 py-1 text-2xs font-semibold transition-colors ${
            mode === m ? 'bg-panel3 text-foreground shadow-sm' : 'text-mutedForeground hover:text-foreground'
          }`}
        >
          {MODE_LABEL[m]}
        </button>
      ))}
    </div>
  )
}

// Render children only in the given mode. Children may be server components.
export function ModeGate({ mode, children }: { mode: ViewMode; children: ReactNode }) {
  const { mode: current } = useViewMode()
  if (current !== mode) return null
  return <>{children}</>
}

// Semantic wrappers for the M8.11 guided layer.
export function BeginnerOnly({ children }: { children: ReactNode }) {
  return <ModeGate mode="simple">{children}</ModeGate>
}
export function ProOnly({ children }: { children: ReactNode }) {
  return <ModeGate mode="terminal">{children}</ModeGate>
}
