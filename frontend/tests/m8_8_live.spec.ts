import { test, expect } from '@playwright/test'
import path from 'path'

const screenshotDir = path.join(__dirname, '../../screenshots')

test.describe('M8.8 live stream UI', () => {
  test('dashboard shows explanation cards and live status badge', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('What does this dashboard mean?')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('live-market-strip')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('live-market-strip').getByTestId('live-status-badge')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_8_dashboard.png'), fullPage: true })
  })

  test('live monitor page shows stream debug panel', async ({ page }) => {
    await page.goto('/live')
    await expect(page.getByText('Live Market Monitor')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('stream-debug-panel')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('live-market-strip')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_8_live_monitor.png'), fullPage: true })
  })

  test('ticker page shows chart provider badge', async ({ page }) => {
    await page.goto('/ticker/PLTR')
    await expect(page.getByTestId('price-chart')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('chart-provider-badge')).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'm8_8_ticker_PLTR.png'), fullPage: true })
  })
})
