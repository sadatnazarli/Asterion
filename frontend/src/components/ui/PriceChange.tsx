import { direction, isNum, money, pct } from '@/lib/format'

// Colored price-change display. Green up / red down / dim flat. Arrow optional.
export function PriceChange({
  change,
  changePct,
  size = 'sm',
  arrow = true,
  className = '',
}: {
  change?: number | null
  changePct?: number | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  arrow?: boolean
  className?: string
}) {
  const dir = direction(isNum(changePct) ? changePct : change)
  const color = dir === 'up' ? 'text-up' : dir === 'down' ? 'text-down' : 'text-mutedForeground'
  const sizes = {
    xs: 'text-2xs',
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }
  const glyph = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '–'
  const parts: string[] = []
  if (isNum(change)) parts.push(money(change, { decimals: 2 }).replace('$-', '-$'))
  if (isNum(changePct)) parts.push(`(${pct(changePct, { signed: true })})`)

  return (
    <span className={`num inline-flex items-center gap-1 ${color} ${sizes[size]} ${className}`}>
      {arrow && <span className="text-[0.8em]">{glyph}</span>}
      {parts.length ? parts.join(' ') : '—'}
    </span>
  )
}
