import { test, expect, type Page } from '@playwright/test'
import path from 'path'

const SHOT_DIR = path.resolve(__dirname, '../../screenshots')
test.use({ viewport: { width: 1600, height: 1000 } })

async function dismissOnboarding(page: Page) {
  const modal = page.locator('[data-testid="onboarding-modal"]')
  if (await modal.isVisible().catch(() => false)) {
    await page.locator('[data-testid="onboarding-dismiss"]').click()
    await expect(modal).toBeHidden()
  }
}

test('onboarding modal shows on first launch and can be dismissed', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  const modal = page.locator('[data-testid="onboarding-modal"]')
  await expect(modal).toBeVisible()
  await expect(page.getByText('Welcome to Asterion')).toBeVisible()
  await page.waitForTimeout(400)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_11_onboarding.png') })
  await page.locator('[data-testid="onboarding-dismiss"]').click()
  await expect(modal).toBeHidden()
  // stays dismissed on reload (localStorage flag)
  await page.reload({ waitUntil: 'networkidle' })
  await expect(modal).toBeHidden()
})

test('dashboard beginner mode: help box, reading order, explains, checklist, no buy/sell', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await dismissOnboarding(page)
  await expect(page.locator('[data-testid="help-box"]')).toBeVisible()
  await expect(page.locator('[data-testid="reading-order"]')).toBeVisible()
  await expect(page.locator('[data-testid="asterion-explains"]')).toBeVisible()
  await expect(page.locator('[data-testid="action-checklist"]')).toBeVisible()
  await expect(page.getByText('This page answers:').first()).toBeVisible()
  const body = (await page.locator('body').innerText()).toLowerCase()
  expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
  expect(body).toContain('asterion never tells you to buy or sell')
  await page.waitForTimeout(800)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_11_dashboard_beginner.png'), fullPage: true })
})

test('tooltips render and reveal a definition on hover', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await dismissOnboarding(page)
  const tips = page.locator('[data-testid="help-tip"]')
  expect(await tips.count()).toBeGreaterThan(0)
  await tips.first().hover()
  await expect(page.getByRole('tooltip').filter({ hasText: 'Everything you own added up' })).toBeVisible()
})

test('pro mode hides the beginner guidance', async ({ page }) => {
  await page.goto('/dashboard', { waitUntil: 'networkidle' })
  await dismissOnboarding(page)
  await page.locator('[data-testid="mode-toggle"]').getByText('Pro').click()
  await expect(page.locator('[data-testid="reading-order"]')).toBeHidden()
  await expect(page.locator('[data-testid="help-box"]')).toBeHidden()
})

test('per-page help boxes render across the app', async ({ page }) => {
  for (const [route, answer] of [
    ['/market', 'Is the whole market moving'],
    ['/portfolio', 'Where is my money?'],
    ['/risk', 'What could hurt me?'],
    ['/ticker/PLTR', 'strong, risky, or overpriced'],
  ] as const) {
    await page.goto(route, { waitUntil: 'networkidle' })
    await dismissOnboarding(page)
    await expect(page.getByText(answer, { exact: false }).first()).toBeVisible()
    const body = (await page.locator('body').innerText()).toLowerCase()
    expect(body).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
  }
})

test('screenshots: market + ticker beginner', async ({ page }) => {
  await page.goto('/market', { waitUntil: 'networkidle' })
  await dismissOnboarding(page)
  await page.locator('[data-testid="price-chart"]').first().waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {})
  await page.waitForTimeout(2500)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_11_market_beginner.png'), fullPage: true })

  await page.goto('/ticker/PLTR', { waitUntil: 'networkidle' })
  await dismissOnboarding(page)
  await page.waitForTimeout(2200)
  await page.screenshot({ path: path.join(SHOT_DIR, 'm8_11_ticker_beginner.png'), fullPage: true })
})
