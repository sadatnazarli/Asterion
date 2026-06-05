import { test, expect } from '@playwright/test'

// M13 — capture Scanner + IPO screens for the README gallery.
// Run with the app already up on :3000 (see make start). Outputs land in
// ../screenshots and are curated into docs/assets/screenshots by hand.

test.use({ viewport: { width: 1600, height: 1000 } })

// Skip the first-run onboarding modal and force the dense Pro (terminal) view.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('asterion-onboarded', '1')
    window.localStorage.setItem('asterion-view-mode', 'terminal')
  })
})

async function settle(page: import('@playwright/test').Page) {
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(700) // let bars/transitions paint
}

test('scanner — ranked screen (calibrated)', async ({ page }) => {
  // The app shell is a fixed-height flex with an inner scroll container, so a
  // tall viewport (not fullPage) is what reveals more of the ranked list.
  await page.setViewportSize({ width: 1600, height: 1500 })
  await page.goto('/scanner', { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('Opportunity Scanner').first()).toBeVisible()
  await settle(page)
  await page.screenshot({ path: '../screenshots/m13_scanner.png' })
})

test('ipo — SpaceX research-only scorecard', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 2400 })
  await page.goto('/ipo/SPACEX', { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('IPO / Private Company Mode', { exact: true }).first()).toBeVisible()
  await settle(page)
  await page.screenshot({ path: '../screenshots/m13_ipo_spacex.png' })
})
