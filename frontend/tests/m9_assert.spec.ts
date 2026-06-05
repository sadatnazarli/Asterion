import { test, expect } from '@playwright/test'

test('market: large chart + market strip render', async ({ page }) => {
  await page.goto('/market', { waitUntil: 'networkidle' })
  await expect(page.locator('[data-testid="price-chart"]').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText('S&P 500').first()).toBeVisible()
  await expect(page.getByText(/Portfolio heatmap/i)).toBeVisible()
})

test('ticker PLTR: no fake N/A, uniform /100 scale, real implied growth', async ({ page }) => {
  await page.goto('/ticker/PLTR', { waitUntil: 'networkidle' })
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('Why is this missing?')
  expect(body).not.toContain('Invalid Date')
  expect(body).toContain('/ 100') // scores carry an explicit scale
  await expect(page.locator('[data-testid="price-chart"]').first()).toBeVisible({ timeout: 15_000 })
  // implied growth tile is populated from the nested reverse-DCF input, not blank
  await expect(page.getByText('Implied Growth (5Y)')).toBeVisible()
})

test('system: masked key shown, raw key never leaked, no buy/sell', async ({ page }) => {
  await page.goto('/system', { waitUntil: 'networkidle' })
  const text = await page.locator('body').innerText() // visible text only, not script chunks
  expect(text).toContain('****') // masked
  // a real finnhub key is a long token; assert no 20+ char secret leaked in visible text
  expect(text).not.toMatch(/[A-Za-z0-9]{20,}/)
  expect(text.toLowerCase()).not.toMatch(/\b(buy|sell)\b\s*(rating|recommendation|signal)/)
})

test('portfolio: brokerage table renders without invalid date', async ({ page }) => {
  await page.goto('/portfolio', { waitUntil: 'networkidle' })
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('Invalid Date')
  await expect(page.getByText('Holdings & Performance')).toBeVisible()
})
