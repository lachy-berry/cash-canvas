// @ts-check
import { test, expect, request as apiRequest } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SAMPLE_CSV = path.join(__dirname, '../fixtures/sample.csv')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Clear all transactions and batches via the API between tests. */
async function clearDB(request) {
  // Fetch all batches and delete them — cascades to transactions
  const res = await request.get('http://localhost:8000/api/transactions?limit=500')
  if (!res.ok()) return
  const data = await res.json()
  const batchIds = [...new Set(
    (data.transactions || []).map(t => t.batch_id).filter(Boolean)
  )]
  for (const id of batchIds) {
    await request.delete(`http://localhost:8000/api/import/batches/${id}`)
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('CSV Import', () => {
  test.beforeEach(async ({ request }) => {
    await clearDB(request)
  })

  test('shows an "Import CSV" link or button on the home page', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: /import/i }).or(
      page.getByRole('button', { name: /import/i })
    )).toBeVisible()
  })

  test('clicking Import CSV navigates to /import', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /import/i }).or(
      page.getByRole('button', { name: /import/i })
    ).first().click()
    await expect(page).toHaveURL(/\/import/)
  })

  test('uploading sample.csv shows pre-filled column mapping dropdowns', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    // After file selection the column mapping step should appear
    await expect(page.getByText(/date/i).first()).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/description/i).first()).toBeVisible()
    await expect(page.getByText(/amount/i).first()).toBeVisible()
  })

  test('proceeding shows review step with 10 new transactions', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    // Click through mapping step
    await page.getByRole('button', { name: /next|continue|review/i }).click()
    await expect(page.getByText(/10 new/i)).toBeVisible({ timeout: 5000 })
  })

  test('importing shows success with "Imported 10 transactions"', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    await page.getByRole('button', { name: /next|continue|review/i }).click()
    await page.getByRole('button', { name: /import/i }).click()
    await expect(page.getByText(/imported 10 transactions/i)).toBeVisible({ timeout: 5000 })
  })

  test('after import, clicking "View transactions" shows WOOLWORTHS in the list', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    await page.getByRole('button', { name: /next|continue|review/i }).click()
    await page.getByRole('button', { name: /import/i }).click()
    await page.getByRole('link', { name: /view transactions/i }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByText(/WOOLWORTHS/i)).toBeVisible({ timeout: 5000 })
  })

  test('importing same file twice shows 10 duplicates in review step', async ({ page, request }) => {
    // First import via API to seed the DB
    const formData = new FormData()
    formData.append('date_col', 'Date')
    formData.append('desc_col', 'Description')
    formData.append('amount_col', 'Amount')
    formData.append('balance_col', 'Balance')
    const fs = await import('fs')
    const csvBytes = fs.readFileSync(SAMPLE_CSV)
    formData.append('file', new Blob([csvBytes], { type: 'text/csv' }), 'bank.csv')

    const previewRes = await request.post('http://localhost:8000/api/import/preview', {
      multipart: {
        date_col: 'Date',
        desc_col: 'Description',
        amount_col: 'Amount',
        balance_col: 'Balance',
        file: {
          name: 'bank.csv',
          mimeType: 'text/csv',
          buffer: csvBytes,
        },
      },
    })
    const previewData = await previewRes.json()
    await request.post('http://localhost:8000/api/import/confirm', {
      data: { rows: previewData.new },
    })

    // Now go through the UI for the second import
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    await page.getByRole('button', { name: /next|continue|review/i }).click()
    await expect(page.getByText(/10 duplicate/i)).toBeVisible({ timeout: 5000 })
  })

  test('undo button removes the batch and transaction list returns to 0', async ({ page, request }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CSV)
    await page.getByRole('button', { name: /next|continue|review/i }).click()
    await page.getByRole('button', { name: /import/i }).click()
    await expect(page.getByText(/imported 10/i)).toBeVisible({ timeout: 5000 })

    // Undo
    await page.getByRole('button', { name: /undo/i }).click()

    // Go home and verify list is empty
    await page.goto('/')
    await expect(page.getByText(/no transactions/i)).toBeVisible({ timeout: 5000 })
  })

  test('CSV with no recognisable columns shows unmapped dropdowns', async ({ page }) => {
    await page.goto('/import')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'weird.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('Foo,Bar,Baz\n1,2,3\n'),
    })
    // Mapping step should appear but all dropdowns should be blank / unselected
    await expect(page.getByText(/map|column/i).first()).toBeVisible({ timeout: 3000 })
    // None of the selects should have a pre-filled value matching our fields
    const selects = page.locator('select')
    const count = await selects.count()
    let anyPrefilled = false
    for (let i = 0; i < count; i++) {
      const val = await selects.nth(i).inputValue()
      if (val && val !== '') anyPrefilled = true
    }
    expect(anyPrefilled).toBe(false)
  })
})
