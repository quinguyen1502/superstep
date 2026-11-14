import { expect, test } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'

test('warns before a Dataset write and links to the preselected grant', async ({ page, context }) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: 'Run feedback dataset', columns: [{ key: 'ticket', label: 'Ticket', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const wid = await newWorkflow(page, headers, {
    name: 'Dataset run feedback',
    state: [{ name: 'result', type: 'object' }],
    nodes: [
      N('start', 'start', 40),
      N('data', 'dataset', 300, { dataset_id: dataset.id, operation: 'insert_row', fields: [],
        arguments: { values: { ticket: 'Created' } }, output_field: 'result' }),
      N('end', 'end', 560),
    ],
    edges: [{ id: 'a', source: 'start', target: 'data' }, { id: 'b', source: 'data', target: 'end' }],
  })
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="data"]').click()
  await page.locator('#config-tab-settings').click()
  const popupPromise = context.waitForEvent('page')
  await page.getByRole('link', { name: 'Grant access' }).click()
  const popup = await popupPromise
  await expect(popup.getByRole('tabpanel', { name: 'Access' })).toBeVisible()
  await expect(popup.getByRole('combobox', { name: 'Workflow', exact: true })).toContainText('Dataset run feedback')
  await popup.close()

  await page.locator('#run-btn').click()
  const notice = page.getByRole('alertdialog', { name: 'This run can change Dataset rows' })
  await expect(notice).toBeVisible()
  await notice.getByRole('button', { name: 'Cancel' }).click()
  await page.locator('#run-btn').click()
  await notice.getByRole('button', { name: 'Run', exact: true }).click()
  await expect(notice).toHaveCount(0)
  await expect(page.locator('#run-btn')).toBeEnabled()
  await page.locator('#run-btn').click()
  await expect(notice).toHaveCount(0)
})
