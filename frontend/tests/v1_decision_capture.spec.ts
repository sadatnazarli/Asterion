import { test, expect } from '@playwright/test'

// V1 — capture the decision-intelligence page for the integration report.
test.use({ viewport: { width: 1600, height: 1400 } })

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('asterion-onboarded', '1')
    window.localStorage.setItem('asterion-view-mode', 'terminal')
  })
})

test('decision — spacex combined risk', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1600 })
  await page.goto('/decision/SPACEX', { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('Decision Intelligence — Financial + Compliance').first()).toBeVisible()
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(600)
  await page.screenshot({ path: '../screenshots/v1_decision_spacex.png' })
})
