// @ts-check
/**
 * E2E tests for Feature #3: Transaction Labelling
 *
 * These tests are written BEFORE any implementation exists (ATDD step 2).
 * All tests are expected to FAIL until the feature is built.
 *
 * User journey:
 *  1. Import transactions
 *  2. On the home page, each transaction row shows a category dropdown
 *  3. User selects a label → saved immediately via PATCH
 *  4. After page reload, the label is still shown
 *  5. User can clear a label by selecting the blank/unset option
 */
import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SAMPLE_CSV = path.join(__dirname, '../fixtures/sample.csv')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seed the DB with sample.csv via the API. */
async function seedImport(request) {
  const fs = await import('fs')
  const csvBytes = fs.readFileSync(SAMPLE_CSV)

  const previewRes = await request.post('http://localhost:8000/api/import/preview', {
    multipart: {
      date_col: 'Date',
      desc_col: 'Description',
      amount_col: 'Amount',
      balance_col: 'Balance',
      file: { name: 'bank.csv', mimeType: 'text/csv', buffer: csvBytes },
    },
  })
  const preview = await previewRes.json()
  await request.post('http://localhost:8000/api/import/confirm', {
    data: { rows: preview.new ?? [] },
  })
}

/** Wipe DB via test reset endpoint. */
async function resetDB(request) {
  await request.delete('http://localhost:8000/api/test/reset')
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Labelling', () => {
  test.beforeEach(async ({ request }) => {
    await resetDB(request)
    await seedImport(request)
  })

  test('each transaction row shows a category dropdown', async ({ page }) => {
    await page.goto('/')
    // At least one label picker (select or combobox) should be visible per row
    const pickers = page.locator('[data-testid="label-picker"]')
    await expect(pickers.first()).toBeVisible({ timeout: 5000 })
    const count = await pickers.count()
    // sample.csv has 10 transactions (default page size ≥ 10)
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('selecting a label saves it and shows it immediately', async ({ page }) => {
    await page.goto('/')

    // Pick the first label-picker and select "Groceries"
    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })
    await firstPicker.selectOption({ label: 'Groceries' })

    // The same dropdown must now display "Groceries" (no page reload yet)
    await expect(firstPicker).toHaveValue('groceries')
  })

  test('label persists after page reload', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })
    await firstPicker.selectOption({ label: 'Groceries' })

    // Reload and check the label is still selected
    await page.reload()
    const reloadedPicker = page.locator('[data-testid="label-picker"]').first()
    await reloadedPicker.waitFor({ state: 'visible', timeout: 5000 })
    await expect(reloadedPicker).toHaveValue('groceries')
  })

  test('clearing a label restores the blank/unset state', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })

    // Set a label first
    await firstPicker.selectOption({ label: 'Groceries' })
    await expect(firstPicker).toHaveValue('groceries')

    // Clear it by selecting the empty option
    await firstPicker.selectOption({ value: '' })
    await expect(firstPicker).toHaveValue('')

    // Reload and confirm it's gone
    await page.reload()
    const reloadedPicker = page.locator('[data-testid="label-picker"]').first()
    await reloadedPicker.waitFor({ state: 'visible', timeout: 5000 })
    await expect(reloadedPicker).toHaveValue('')
  })

  test('all broad categories appear as options in the dropdown', async ({ page }) => {
    await page.goto('/')
    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })

    // These are the category IDs from config/categories.yaml
    const expectedValues = [
      'groceries', 'dining', 'transport', 'utilities',
      'health', 'entertainment', 'income', 'other',
    ]
    for (const value of expectedValues) {
      const option = firstPicker.locator(`option[value="${value}"]`)
      await expect(option).toHaveCount(1)
    }
  })

  test('label picker shows an inline error if the API call fails', async ({ page }) => {
    await page.goto('/')

    // Intercept the PATCH and force a 500 error
    await page.route('**/api/transactions/*/labels', (route) => {
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    })

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })
    await firstPicker.selectOption({ label: 'Groceries' })

    // An error message must appear (exact wording flexible — check for key words)
    await expect(page.getByText(/error|failed|could not/i).first()).toBeVisible({ timeout: 5000 })
  })
})
