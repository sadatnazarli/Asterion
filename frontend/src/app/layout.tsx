import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { TerminalShell } from '@/components/ui/TerminalShell'

const inter = Inter({ subsets: ['latin'], variable: '--font-ui' })
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' })

export const metadata: Metadata = {
  title: 'Asterion Terminal',
  description: 'Local-first institutional-grade equity intelligence',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${mono.variable}`}>
      <body suppressHydrationWarning className="font-sans">
        <TerminalShell>{children}</TerminalShell>
      </body>
    </html>
  )
}
