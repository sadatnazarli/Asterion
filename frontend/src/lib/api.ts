const API_BASE =
  process.env.NEXT_PUBLIC_ASTERION_API_URL ||
  process.env.ASTERION_API_URL ||
  'http://127.0.0.1:8000'

export function getApiBase(): string {
  return API_BASE
}

export function getWsBase(): string {
  return API_BASE.replace(/^http/, 'ws')
}

export async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${getApiBase()}${path}`, { cache: 'no-store' })
    if (!res.ok) return null
    return res.json() as Promise<T>
  } catch {
    return null
  }
}
