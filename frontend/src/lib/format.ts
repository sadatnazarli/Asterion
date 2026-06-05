// Centralized number/format helpers. Distinguishes "real zero" from "missing"
// so the UI never prints a misleading N/A on a valid 0 (see audit §6).

export function isNum(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

export function money(v: unknown, opts: { decimals?: number } = {}): string {
  if (!isNum(v)) return '—'
  const d = opts.decimals ?? 2
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`
}

export function compactMoney(v: unknown): string {
  if (!isNum(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(v / 1e3).toFixed(2)}K`
  return money(v)
}

export function pct(v: unknown, opts: { decimals?: number; signed?: boolean } = {}): string {
  if (!isNum(v)) return '—'
  const d = opts.decimals ?? 2
  const s = opts.signed && v > 0 ? '+' : ''
  return `${s}${v.toFixed(d)}%`
}

// value stored as a fraction (0.25) -> "25.00%"
export function pctFrac(v: unknown, opts: { decimals?: number; signed?: boolean } = {}): string {
  if (!isNum(v)) return '—'
  return pct(v * 100, opts)
}

export function num(v: unknown, decimals = 2): string {
  if (!isNum(v)) return '—'
  return v.toFixed(decimals)
}

// 0-100 score with explicit scale; preserves a real 0
export function score100(v: unknown, decimals = 1): string {
  if (!isNum(v)) return '—'
  return `${v.toFixed(decimals)} / 100`
}

export function direction(v: unknown): 'up' | 'down' | 'flat' {
  if (!isNum(v) || v === 0) return 'flat'
  return v > 0 ? 'up' : 'down'
}

export function timeAgo(iso: string | number | null | undefined): string {
  if (iso === null || iso === undefined) return 'unknown'
  const t = typeof iso === 'number' ? iso * (iso < 1e12 ? 1000 : 1) : Date.parse(iso)
  if (Number.isNaN(t)) return 'unknown'
  const secs = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return `${Math.floor(secs / 86400)}d ago`
}

export function safeDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return new Date(t).toLocaleString()
}
