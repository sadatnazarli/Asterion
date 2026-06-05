import { test, expect } from '@playwright/test'
import path from 'path'

const screenshotDir = path.join(__dirname, '../../screenshots')

test('live monitor shows Finnhub connected', async ({ page }) => {
  await page.goto('/live')
  await expect(page.getByText('Live Market Monitor')).toBeVisible()
  await expect(page.getByTestId('stream-debug-panel')).toContainText('finnhub_ws', { timeout: 20_000 })
  await expect(page.getByTestId('live-market-strip').getByTestId('live-status-badge')).not.toContainText('Polling fallback')
  await page.screenshot({ path: path.join(screenshotDir, 'm8_8_live_finnhub.png'), fullPage: true })
})
