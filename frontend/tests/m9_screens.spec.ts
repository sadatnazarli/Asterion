import { test, expect } from '@playwright/test'
import path from 'path'

const SHOT_DIR = path.resolve(__dirname, '../../screenshots')
test.use({ viewport: { width: 1600, height: 1000 } })

const pages: { route: string; file: string; waitChart?: boolean }[] = [
  { route: '/market', file: 'final_market_terminal.png', waitChart: true },
  { route: '/dashboard', file: 'final_dashboard.png' },
  { route: '/ticker/PLTR', file: 'final_ticker_PLTR.png', waitChart: true },
  { route: '/portfolio', file: 'final_portfolio.png' },
  { route: '/risk', file: 'final_risk.png' },
  { route: '/coverage', file: 'final_coverage.png' },
  { route: '/system', file: 'provider_status.png' },
]

for (const p of pages) {
  test(`screenshot ${p.route}`, async ({ page }) => {
    await page.goto(p.route, { waitUntil: 'networkidle' })
    // let the market top strip + any chart settle
    if (p.waitChart) {
      await page.locator('[data-testid="price-chart"]').first().waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {})
    }
    await page.waitForTimeout(2500)
    await page.screenshot({ path: path.join(SHOT_DIR, p.file), fullPage: true })
  })
}
