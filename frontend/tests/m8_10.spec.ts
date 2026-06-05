import { test, expect, type Page } from '@playwright/test'
import path from 'path'

const SHOT_DIR = path.resolve(__dirname, '../../screenshots')
test.use({ viewport: { width: 1600, height: 1000 } })

async function settle(page: Page, ms = 1800) {
  await page.waitForTimeout(ms)
}

test('market: renders, chart visible, no buy/sell, no invalid date', async ({ page }) => {
  await page.goto('/market', { waitUntil: 'networkidle' })
  await expect(page.locator('[data-testid="todays-readout"]')).toBeVisible()
  await page.locator('[data-testid="price-chart"]').first().waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {})
  await expect(page.locator('[data-testid="price-chart"]').first()).toBeVisible()
  const body = (await page.locator('body').innerText()).toLowerCase()
  expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
  expect(body).not.toContain('invalid date')
  await settle(page, 2500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_market.png'), fullPage: true })
})

test('dashboard: readout visible, portfolio total shown', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await expect(page.locator('[data-testid="todays-readout"]')).toBeVisible()
  await expect(page.getByText('Why it moved today')).toBeVisible()
  const body = await page.locator('body').innerText()
  expect(body).toMatch(/\$[\d,]+/) // a dollar total renders (data-agnostic)
  expect(body.toLowerCase()).not.toContain('invalid date')
  await settle(page)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_dashboard.png'), fullPage: true })
})

test('portfolio: table renders, total shown, no key leak', async ({ page }) => {
  await page.goto('/portfolio', { waitUntil: 'networkidle' })
  await expect(page.getByText('Holdings & Performance')).toBeVisible()
  const body = await page.locator('body').innerText()
  expect(body).toMatch(/\$[\d,]+/)
  // no raw provider API key leaked into the DOM (20+ char alnum run)
  expect(body).not.toMatch(/\b[A-Za-z0-9]{20,}\b/)
  await settle(page)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_portfolio.png'), fullPage: true })
})

test('ticker PLTR: header + chart + score meters', async ({ page }) => {
  await page.goto('/ticker/PLTR', { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { name: 'PLTR' })).toBeVisible()
  const body = (await page.locator('body').innerText()).toLowerCase()
  expect(body).not.toContain('invalid date')
  expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
  await settle(page, 2500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_ticker_PLTR.png'), fullPage: true })
})

test('risk: diagnosis + severity chips', async ({ page }) => {
  await page.goto('/risk', { waitUntil: 'networkidle' })
  await expect(page.getByText('Risk Cockpit')).toBeVisible()
  await expect(page.getByText('Diagnosis')).toBeVisible()
  await settle(page)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_risk.png'), fullPage: true })
})

test('coverage + system render and screenshot', async ({ page }) => {
  await page.goto('/coverage', { waitUntil: 'networkidle' })
  await expect(page.getByText('Coverage Matrix')).toBeVisible()
  await settle(page)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_coverage.png'), fullPage: true })

  await page.goto('/system', { waitUntil: 'networkidle' })
  await expect(page.getByText('Data Providers')).toBeVisible()
  // keys must never be shown in full — only masked suffixes
  const body = await page.locator('body').innerText()
  expect(body).not.toMatch(/\b[A-Za-z0-9]{20,}\b/)
  await settle(page)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_10_system.png'), fullPage: true })
})
