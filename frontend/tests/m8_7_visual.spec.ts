import { test, expect } from '@playwright/test'
import path from 'path'

const screenshotDir = path.join(__dirname, '../../screenshots')

test.describe('M8.7 visual rendering', () => {
  test('dashboard shows charts and correct portfolio total', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('What does this dashboard mean?')).toBeVisible({ timeout: 15_000 })
    await page.locator('text=Top holdings').scrollIntoViewIfNeeded()
    await expect(page.getByTestId('holdings-chart')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('theme-chart')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('live-market-strip')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_7_dashboard.png'), fullPage: true })
  })

  test('portfolio page renders holdings chart', async ({ page }) => {
    await page.goto('/portfolio')
    await expect(page.getByTestId('holdings-chart')).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: path.join(screenshotDir, 'm8_7_portfolio.png'), fullPage: true })
  })

  test('coverage page loads', async ({ page }) => {
    await page.goto('/coverage')
    await expect(page.getByText('Portfolio Coverage Matrix')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_7_coverage.png'), fullPage: true })
  })

  test('risk page renders concentration and theme charts', async ({ page }) => {
    await page.goto('/risk')
    await expect(page.getByTestId('holdings-chart')).toBeVisible()
    await expect(page.getByTestId('theme-chart')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_7_risk.png'), fullPage: true })
  })

  test('PLTR ticker page has price chart container', async ({ page }) => {
    await page.goto('/ticker/PLTR')
    await expect(page.getByTestId('price-chart')).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: path.join(screenshotDir, 'm8_7_ticker_PLTR.png'), fullPage: true })
  })
})
