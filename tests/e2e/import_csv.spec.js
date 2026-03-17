// @ts-check
import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SAMPLE_CSV = path.join(__dirname, '../fixtures/sample.csv')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seed the DB with sample.csv via the API and return the batch_id. */
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
  const rows = [...(preview.new ?? []), ...(preview.duplicates ?? [])]

  const confirmRes = await request.post('http://localhost:8000/api/import/confirm', {
    data: { rows },
  })
  const confirm = await confirmRes.json()
  return confirm.batch_id
}

/** Wipe all transactions and batches via the test-only reset endpoint. */
async function resetDB(request) {
  await request.delete('http://localhost:8000/api/test/reset')
}

/**
 * Upload the file and wait for the mapping step to appear.
 * The file picker is hidden so we set files on the input directly,
 * then wait for the mapping UI to render.
 */
async function uploadAndWaitForMapping(page, filePath) {
  await page.locator('input[type="file"]').setInputFiles(filePath)
  // Wait for the column mapping form to appear (indicated by a select element)
  await page.locator('select').first().waitFor({ state: 'visible', timeout: 5000 })
}

/**
 * Click the "Review import →" button and wait for the review step.
 */
async function proceedToReview(page) {
  await page.getByRole('button', { name: /Review import/i }).click()
  // Wait for the review step heading to appear
  await page.getByRole('heading', { name: /Review import/i }).waitFor({ timeout: 10000 })
  // Wait for the preview API to resolve — the summary paragraph updates
  await page.locator('p').filter({ hasText: /ready to import/i }).waitFor({ timeout: 10000 })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('CSV Import', () => {
  test.beforeEach(async ({ request }) => {
    await resetDB(request)
  })

  test('shows an "Import CSV" link or button on the home page', async ({ page }) => {
    await page.goto('/')
    await expect(
      page.getByRole('link', { name: /import csv/i }).or(page.getByRole('button', { name: /import csv/i }))
    ).toBeVisible()
  })

  test('clicking Import CSV navigates to /import', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /import csv/i }).click()
    await expect(page).toHaveURL(/\/import/)
  })

  test('uploading sample.csv shows pre-filled column mapping dropdowns', async ({ page }) => {
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)

    // The Date select should be pre-filled with "Date" (the matched header)
    const dateSelect = page.locator('select').first()
    await expect(dateSelect).toHaveValue('Date')

    // Description select should be pre-filled too
    const descSelect = page.locator('select').nth(1)
    await expect(descSelect).toHaveValue('Description')
  })

  test('proceeding shows review step with 10 new transactions', async ({ page }) => {
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)
    await expect(page.getByText(/10 new/i).first()).toBeVisible()
  })

  test('importing shows success with "Imported 10 transactions"', async ({ page }) => {
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)

    // Click the Import button (text is "Import 10 transactions")
    await page.getByRole('button', { name: /Import 10 transaction/i }).click()
    await expect(page.getByText(/Imported 10 transactions/i)).toBeVisible({ timeout: 10000 })
  })

  test('after import, clicking "View transactions" shows WOOLWORTHS in the list', async ({ page }) => {
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)
    await page.getByRole('button', { name: /Import 10 transaction/i }).click()
    await expect(page.getByText(/Imported 10 transactions/i)).toBeVisible({ timeout: 10000 })

    await page.getByRole('link', { name: /view transactions/i }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByText(/WOOLWORTHS/i).first()).toBeVisible({ timeout: 5000 })
  })

  test('importing same file twice shows 10 duplicates in review step', async ({ page, request }) => {
    // Seed the DB with the first import via API
    await seedImport(request)

    // Go through the UI for the second import
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)

    await expect(page.getByRole('heading', { name: /10 possible duplicate/i })).toBeVisible({ timeout: 5000 })
  })

  test('undo button removes the batch and transaction list returns to 0', async ({ page }) => {
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)
    await page.getByRole('button', { name: /Import 10 transaction/i }).click()
    await expect(page.getByText(/Imported 10 transactions/i)).toBeVisible({ timeout: 10000 })

    // Undo
    await page.getByRole('button', { name: /undo this import/i }).click()
    await expect(page.getByText(/import undone/i)).toBeVisible({ timeout: 5000 })

    // Go home and verify the list is empty
    await page.goto('/')
    await expect(page.getByText(/no transactions/i)).toBeVisible({ timeout: 5000 })
  })

  test('skipped count shown on Step 4 when duplicates were not included', async ({ page, request }) => {
    // Seed all 10 rows via API first so second import sees them all as duplicates
    await seedImport(request)

    // Import the same file via UI — all 10 will be duplicates
    // Include only the first one, skip the other 9
    await page.goto('/import')
    await uploadAndWaitForMapping(page, SAMPLE_CSV)
    await proceedToReview(page)

    // Click "+ Include anyway" only on the first duplicate row
    const includeButtons = page.getByRole('button', { name: /include anyway/i })
    await includeButtons.first().click()

    // Import: 1 included, 9 skipped
    await page.getByRole('button', { name: /Import 1 transaction/i }).click()

    // Step 4 should report the correct skipped count
    await expect(page.getByText(/9 duplicate/i)).toBeVisible({ timeout: 10000 })
  })

  test('CSV with no recognisable columns shows unmapped dropdowns', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'weird.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('Foo,Bar,Baz\n1,2,3\n'),
    })
    // Wait for mapping UI to appear
    await page.locator('select').first().waitFor({ state: 'visible', timeout: 5000 })

    // All selects should have empty values (no pre-fill matched)
    const selects = page.locator('select')
    const count = await selects.count()
    for (let i = 0; i < count; i++) {
      await expect(selects.nth(i)).toHaveValue('')
    }
  })
})
