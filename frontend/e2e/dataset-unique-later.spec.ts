import { expect, test, type Page } from '@playwright/test'
import { signIn } from './helpers'

async function openColumn(page: Page, label: string) {
  await page.getByRole('button', { name: 'Dataset actions' }).click()
  await page.getByRole('menuitem', { name: 'View schema', exact: true }).click()
  const schema = page.getByRole('dialog', { name: 'Schema', exact: true })
  await schema.getByRole('button', { name: `Edit ${label}` }).click()
  return { schema, editor: page.getByRole('dialog', { name: 'Edit column' }) }
}

test('marks an existing column unique after the duplicate check', async ({ page }, testInfo) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: `Unique later ${Date.now().toString(36)}`,
    columns: [{ key: 'ticket_id', label: 'Ticket ID', kind: 'text' }, { key: 'subject', label: 'Subject', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const rowsUrl = `/api/datasets/${dataset.id}/rows`
  for (const [ticket, subject] of [['T-1', 'First'], ['T-2', 'Second'], ['T-1', 'Copy']]) {
    expect((await page.request.post(rowsUrl, { headers, data: { values: { ticket_id: ticket, subject } } })).ok()).toBeTruthy()
  }

  await page.goto(`/datasets/${dataset.id}`)
  let { editor } = await openColumn(page, 'Ticket ID')
  await expect(editor.getByRole('checkbox', { name: 'Required' })).toBeDisabled()
  await expect(editor.getByText('Required is set when the column is created.')).toBeVisible()
  await editor.getByRole('checkbox', { name: 'Unique' }).click()
  await editor.getByRole('button', { name: 'Save', exact: true }).click()
  const duplicates = editor.getByTestId('dataset-unique-duplicates')
  await expect(duplicates).toContainText('Some rows share a value')
  await expect(duplicates).toContainText('Field ticket_id cannot become unique because 2 rows share a value')
  await expect(duplicates).toContainText('Example row IDs:')
  const icon = (await duplicates.locator('svg').first().boundingBox())!
  const title = (await duplicates.getByText('Some rows share a value').boundingBox())!
  expect(Math.abs(icon.y - title.y)).toBeLessThan(title.height)
  await testInfo.attach('dataset-unique-duplicates', { body: await page.screenshot({ animations: 'disabled' }), contentType: 'image/png' })
  await duplicates.getByRole('button', { name: 'Show rows with T-1' }).click()
  await expect(editor).toHaveCount(0)
  const rows = page.getByTestId('dataset-row')
  await expect(rows).toHaveCount(2)
  await expect(page.getByRole('button', { name: 'Filter', exact: true })).toBeVisible()

  const copy = (await (await page.request.post(`${rowsUrl}/query`, { headers, data: {} })).json()).data.items
    .find((item: { values: { subject: string } }) => item.values.subject === 'Copy')
  expect((await page.request.patch(`${rowsUrl}/${copy.id}`, { headers, data: { revision: copy.revision, values: { ticket_id: 'T-3' } } })).ok()).toBeTruthy()

  ;({ editor } = await openColumn(page, 'Ticket ID'))
  await editor.getByRole('checkbox', { name: 'Unique' }).click()
  await editor.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(editor).toHaveCount(0)
  const schema = page.getByRole('dialog', { name: 'Schema', exact: true })
  await expect(schema.getByRole('row', { name: /Ticket ID.*ticket_id.*Unique/ })).toBeVisible()

  const upsert = await page.request.post(`${rowsUrl}/upsert`, { headers, data: { key: 'ticket_id', values: { ticket_id: 'T-3', subject: 'Updated' } } })
  expect(upsert.ok()).toBeTruthy()
  expect((await upsert.json()).data.inserted).toBe(false)
})
