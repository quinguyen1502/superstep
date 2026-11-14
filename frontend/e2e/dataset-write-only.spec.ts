import { expect, test } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'

test('write-only Dataset access explains identifier-only results in the node and the Access dialog', async ({ page }, info) => {
  await page.addInitScript(() => {
    localStorage.setItem('lang', 'en')
    localStorage.setItem('theme', 'light')
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: `Write-only tickets ${Date.now()}`,
    columns: [{ key: 'ticket', label: 'Ticket', kind: 'text', required: true, unique: true }, { key: 'note', label: 'Note', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const base = `/api/datasets/${dataset.id}`
  const wid = await newWorkflow(page, headers, {
    name: `Write-only workflow ${Date.now()}`, state: [{ name: 'result', type: 'object' }],
    nodes: [N('s', 'start', 40), N('data', 'dataset', 290, {
      label: 'File ticket', dataset_id: dataset.id, operation: 'upsert_row', fields: ['ticket', 'note'], output_field: 'result',
      arguments: { key: 'ticket', values: { ticket: 'T-01' } },
    }), N('e', 'end', 540)],
    edges: [{ id: 'a', source: 's', target: 'data' }, { id: 'b', source: 'data', target: 'e' }],
  })
  const grant = await page.request.put(`${base}/access/grants/${wid}`, { headers, data: { permission: 'write' } })
  expect(grant.ok()).toBeTruthy()

  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="data"]').click()
  await page.locator('#config-tab-data').click()
  const note = page.getByTestId('dataset-write-only-result')
  await expect(note).toContainText('returns only the row ID, its revision')
  await expect(page.getByRole('group', { name: 'Fields to return' })).toHaveCount(0)
  await expect(note).toContainText('Returning fields needs read access')
  await page.screenshot({ path: info.outputPath('dataset-node-write-only.png') })
  await note.getByRole('button', { name: 'Return identifiers only' }).click()
  await expect(note.getByRole('button', { name: 'Return identifiers only' })).toHaveCount(0)
  await page.locator('#save-btn').click()
  await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = await page.request.get(`/api/workflows/${wid}`, { headers })
  expect((await saved.json()).data.nodes.find((node: { id: string }) => node.id === 'data').data.fields).toEqual([])

  await page.goto(`/datasets/${dataset.id}`)
  await page.getByRole('button', { name: 'Dataset actions' }).click()
  await page.getByRole('menuitem', { name: 'Access', exact: true }).click()
  const access = page.getByRole('tabpanel', { name: 'Access' })
  const tokenForm = access.locator('form').nth(1)
  const writeNote = 'never returns cell values'
  await expect(tokenForm.getByText(writeNote, { exact: false })).toHaveCount(0)
  await tokenForm.getByRole('combobox', { name: 'Permission' }).click()
  await page.getByRole('option', { name: 'Write', exact: true }).click()
  await expect(tokenForm.getByText(writeNote, { exact: false })).toBeVisible()
  await page.screenshot({ path: info.outputPath('dataset-access-write-only.png') })
})
