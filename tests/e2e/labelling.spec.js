// @ts-check
/**
 * E2E acceptance tests for Feature #3: Transaction Labelling
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

/** Seed the DB with sample.csv via the API. Returns the number of rows imported. */
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
  const rows = preview.new ?? []
  await request.post('http://localhost:8000/api/import/confirm', {
    data: { rows },
  })
  return rows.length
}

/** Wipe DB via test reset endpoint. */
async function resetDB(request) {
  await request.delete('http://localhost:8000/api/test/reset')
}

/**
 * Fetch the broad category IDs from /api/categories.
 * Returns an array of { id, name } objects for the 'broad' layer.
 */
async function fetchBroadCategories(request) {
  const res = await request.get('http://localhost:8000/api/categories')
  const data = await res.json()
  const broadLayer = data.layers.find((l) => l.id === 'broad')
  return broadLayer ? broadLayer.categories : []
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Labelling', () => {
  test.beforeEach(async ({ request }) => {
    await resetDB(request)
    await seedImport(request)
  })

  test('each visible transaction row has exactly one category dropdown', async ({ page, request }) => {
    await page.goto('/')

    // Wait for the first picker to appear
    const pickers = page.locator('[data-testid="label-picker"]')
    await expect(pickers.first()).toBeVisible({ timeout: 5000 })

    // Count rendered transaction rows in the table body
    const rows = page.locator('tbody tr')
    const rowCount = await rows.count()
    const pickerCount = await pickers.count()

    // Every rendered row must have exactly one label picker — no more, no less
    expect(pickerCount).toBe(rowCount)
  })

  test('selecting a label saves it and shows it immediately', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })
    await firstPicker.selectOption({ label: 'Groceries' })

    // Dropdown must reflect saved value without a page reload
    await expect(firstPicker).toHaveValue('groceries')
  })

  test('label persists after page reload', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })
    await firstPicker.selectOption({ label: 'Groceries' })

    await page.reload()
    const reloadedPicker = page.locator('[data-testid="label-picker"]').first()
    await reloadedPicker.waitFor({ state: 'visible', timeout: 5000 })
    await expect(reloadedPicker).toHaveValue('groceries')
  })

  test('clearing a label restores the blank/unset state', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })

    await firstPicker.selectOption({ label: 'Groceries' })
    await expect(firstPicker).toHaveValue('groceries')

    await firstPicker.selectOption({ value: '' })
    await expect(firstPicker).toHaveValue('')

    await page.reload()
    const reloadedPicker = page.locator('[data-testid="label-picker"]').first()
    await reloadedPicker.waitFor({ state: 'visible', timeout: 5000 })
    await expect(reloadedPicker).toHaveValue('')
  })

  test('dropdown options are driven by /api/categories — not hardcoded', async ({ page, request }) => {
    // Fetch the canonical category list from the API (which reads config/categories.yaml).
    // This ensures the implementation is config-driven: any category added to the YAML
    // must automatically appear in the UI, and any removed must disappear.
    const categories = await fetchBroadCategories(request)
    expect(categories.length).toBeGreaterThan(0)

    await page.goto('/')
    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })

    // Every category returned by the API must appear as an option in the picker
    for (const cat of categories) {
      const option = firstPicker.locator(`option[value="${cat.id}"]`)
      await expect(option).toHaveCount(1)
    }

    // The number of non-blank options must match the API exactly (no extras, no hardcoding)
    const allOptions = firstPicker.locator('option:not([value=""])')
    await expect(allOptions).toHaveCount(categories.length)
  })

  test('label picker shows inline error and reverts value if the API call fails', async ({ page }) => {
    await page.goto('/')

    const firstPicker = page.locator('[data-testid="label-picker"]').first()
    await firstPicker.waitFor({ state: 'visible', timeout: 5000 })

    // Record the value before the failed save (should be empty/unset)
    const valueBefore = await firstPicker.inputValue()

    // Intercept the PATCH and force a server error
    await page.route('**/api/transactions/*/labels', (route) => {
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    })

    await firstPicker.selectOption({ label: 'Groceries' })

    // An inline error message must appear
    await expect(page.getByText(/error|failed|could not/i).first()).toBeVisible({ timeout: 5000 })

    // The picker must revert to its value before the failed save
    await expect(firstPicker).toHaveValue(valueBefore)
  })
})
