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

// The compass star from the Asterion logo, as a compact brand mark.
function LogoMark({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={className} fill="none">
      <circle cx="12" cy="12" r="9" stroke="rgba(245,183,61,0.28)" strokeWidth="0.75" />
      <path
        d="M12 1 L13.25 10.75 L23 12 L13.25 13.25 L12 23 L10.75 13.25 L1 12 L10.75 10.75 Z"
        fill="url(#ast-gold)"
      />
      <circle cx="12" cy="12" r="1.15" fill="#fff4d6" />
      <defs>
        <linearGradient id="ast-gold" x1="12" y1="1" x2="12" y2="23" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffd982" />
          <stop offset="1" stopColor="#c4922b" />
        </linearGradient>
      </defs>
    </svg>
  )
}

export function TerminalShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  return (
    <ModeProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
        <MarketTopStrip />
        <header className="brand-top flex h-11 shrink-0 items-center gap-1 border-b border-white/[0.06] bg-panel px-3">
          <Link href="/market" className="group mr-4 flex items-center gap-2">
            <LogoMark className="h-[18px] w-[18px] transition-transform duration-300 group-hover:rotate-45" />
            <span className="flex items-baseline gap-1.5">
              <span className="text-sm font-bold tracking-[0.18em] text-foreground">ASTERION</span>
              <span className="text-2xs uppercase tracking-label text-faint">terminal</span>
            </span>
          </Link>
          <nav className="flex items-center gap-0.5">
            {NAV.map((item) => {
              const active = pathname === item.href || (item.href !== '/market' && pathname?.startsWith(item.href))
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={`relative rounded px-2.5 py-1.5 text-xs font-medium transition-colors duration-150 ${
                    active
                      ? 'text-foreground'
                      : 'text-mutedForeground hover:bg-white/[0.04] hover:text-foreground'
                  }`}
                >
                  {item.name}
                  {active && (
                    <span className="absolute inset-x-2.5 -bottom-[7px] h-0.5 rounded-full bg-gold shadow-gold" />
                  )}
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
