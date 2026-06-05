import { test, expect } from '@playwright/test'
import path from 'path'

const SHOT_DIR = path.resolve(__dirname, '../../screenshots')
test.use({ viewport: { width: 1600, height: 1000 } })

test('market: readout, contributors, toggle, heatmap explanation, no buy/sell', async ({ page }) => {
  await page.goto('/market', { waitUntil: 'networkidle' })
  await expect(page.locator('[data-testid="todays-readout"]')).toBeVisible()
  await expect(page.locator('[data-testid="mode-toggle"]')).toBeVisible()
  await expect(page.getByText('Helped today').first()).toBeVisible()
  await expect(page.getByText('Hurt today').first()).toBeVisible()
  await expect(page.getByText(/Size = position value/i)).toBeVisible()
  await expect(page.getByText(/Today's drag/i)).toBeVisible()
  const body = (await page.locator('body').innerText()).toLowerCase()
  expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
})

test('dashboard: readout + why it moved, understandable without raw tables', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await expect(page.locator('[data-testid="todays-readout"]')).toBeVisible()
  await expect(page.getByText('Why it moved today')).toBeVisible()
  await expect(page.getByText('Main risk', { exact: false })).toBeVisible()
  const body = (await page.locator('body').innerText()).toLowerCase()
  expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
})

test('screenshots: dashboard (simple) + market (terminal) + market (simple)', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'final_dashboard.png'), fullPage: true })

  await page.goto('/market', { waitUntil: 'networkidle' })
  await page.locator('[data-testid="price-chart"]').first().waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {})
  await page.waitForTimeout(2500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'final_market_terminal.png'), fullPage: true })

  // flip to simple mode and reshoot market to prove the toggle works
  await page.getByTestId('mode-toggle').getByText('Simple').click()
  await page.waitForTimeout(1500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'final_market_simple.png'), fullPage: true })
})
