import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('user can navigate to the dashboard', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: /dashboard/i }).or(
      page.getByRole('button', { name: /dashboard/i })
    )).toBeVisible()
  })

  test('dashboard shows spending by category', async ({ page }) => {
    await page.goto('/')
    test.fixme(true, 'Implement once Dashboard component and /api/dashboard endpoint exist')
  })
})
