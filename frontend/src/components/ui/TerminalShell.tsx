'use client'

import { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MarketTopStrip } from './MarketTopStrip'
import { ModeProvider, ModeToggle } from './ViewMode'
import { OnboardingModal, GuideButton } from '@/components/onboarding/OnboardingModal'

const NAV = [
  { name: 'Market', href: '/market' },
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Portfolio', href: '/portfolio' },
  { name: 'Risk', href: '/risk' },
  { name: 'Coverage', href: '/coverage' },
  { name: 'Reports', href: '/reports' },
  { name: 'Live', href: '/live' },
  { name: 'System', href: '/system' },
]

export function TerminalShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  return (
    <ModeProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
        <MarketTopStrip />
        <header className="flex h-11 shrink-0 items-center gap-1 border-b border-white/[0.06] bg-panel px-3">
          <Link href="/market" className="mr-4 flex items-baseline gap-1.5">
            <span className="text-sm font-bold tracking-[0.18em] text-foreground">ASTERION</span>
            <span className="text-2xs uppercase tracking-label text-faint">terminal</span>
          </Link>
          <nav className="flex items-center gap-0.5">
            {NAV.map((item) => {
              const active = pathname === item.href || (item.href !== '/market' && pathname?.startsWith(item.href))
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative rounded px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    active
                      ? 'text-foreground'
                      : 'text-mutedForeground hover:bg-white/[0.04] hover:text-foreground'
                  }`}
                >
                  {item.name}
                  {active && <span className="absolute inset-x-2.5 -bottom-[7px] h-0.5 rounded-full bg-accent" />}
                </Link>
              )
            })}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <GuideButton />
            <ModeToggle />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
        <OnboardingModal />
      </div>
    </ModeProvider>
  )
}
