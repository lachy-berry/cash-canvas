import { test, expect } from '@playwright/test'

test.describe('Transaction Labelling', () => {
  test('user can assign a category label to a transaction', async ({ page }) => {
    await page.goto('/')
    // Placeholder — selectors will be refined once TransactionList and LabelPicker are built
    // 1. Find an unlabelled transaction
    // 2. Open the label picker
    // 3. Select a category
    // 4. Confirm the label is persisted and visible
    test.fixme(true, 'Implement once TransactionList and LabelPicker components exist')
  })

  test('labelled transaction shows the assigned category', async ({ page }) => {
    await page.goto('/')
    test.fixme(true, 'Implement once TransactionList and LabelPicker components exist')
  })
})
