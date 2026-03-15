import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FIXTURE_CSV = path.join(__dirname, '../fixtures/sample.csv')

test.describe('CSV Import', () => {
  test('user can navigate to the import screen', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: /import/i }).or(
      page.getByRole('button', { name: /import/i })
    )).toBeVisible()
  })

  test('user can upload a CSV and see transactions listed', async ({ page }) => {
    await page.goto('/')
    // Navigate to import — selector will be refined once UI is built
    await page.getByRole('button', { name: /import/i }).click()
    await page.setInputFiles('input[type="file"]', FIXTURE_CSV)
    await page.getByRole('button', { name: /confirm|import/i }).click()
    // At least one transaction from the fixture should appear
    await expect(page.getByText('WOOLWORTHS')).toBeVisible()
  })
})
