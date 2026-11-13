import { expect, test } from '@playwright/test'
import { signIn } from './helpers'

test('adds a required column with a default to rows and clears removed column values', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const name = `Schema limits ${Date.now().toString(36)}`
  const created = await page.request.post('/api/datasets', { headers, data: {
    name, columns: [{ key: 'ticket', label: 'Ticket', kind: 'text' }, { key: 'note', label: 'Note', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const rowsUrl = `/api/datasets/${dataset.id}/rows`
  for (const ticket of ['A', 'B']) {
    expect((await page.request.post(rowsUrl, { headers, data: { values: { ticket, note: `Note ${ticket}` } } })).ok()).toBeTruthy()
  }

  await page.goto(`/datasets/${dataset.id}`)
  await page.getByRole('button', { name: 'Dataset actions' }).click()
  await page.getByRole('menuitem', { name: 'View schema', exact: true }).click()
  const schema = page.getByRole('dialog', { name: 'Schema', exact: true })
  await expect(schema.getByText('2 of 100 columns. Removed columns do not count.')).toBeVisible()
  await schema.getByRole('button', { name: 'Add column' }).click()
  const add = page.getByRole('dialog', { name: 'Add column' })
  await add.getByLabel('Column label').fill('Status')
  await add.getByLabel('Field key').fill('status')
  await add.getByRole('checkbox', { name: 'Required' }).click()
  await expect(add.getByText(/Existing rows get the default value/)).toBeVisible()
  await add.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(add.getByText('A required column needs a default while this dataset has rows')).toBeVisible()
  await add.getByLabel('Default value').fill('Open')
  await add.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(add).toHaveCount(0)
  await expect(schema.getByText('3 of 100 columns. Removed columns do not count.')).toBeVisible()

  await schema.getByRole('row', { name: /Note.*note/ }).getByRole('button', { name: 'Remove column', exact: true }).click()
  const confirm = page.getByRole('alertdialog')
  await expect(confirm).toContainText('clears its values from every row')
  await confirm.getByRole('textbox').fill('Note')
  await confirm.locator('[id$="-submit"]').click()
  await expect(schema.getByText('2 of 100 columns. Removed columns do not count.')).toBeVisible()

  const rows = (await (await page.request.post(`${rowsUrl}/query`, { headers, data: {} })).json()).data.items
  expect(rows.map((row: { values: Record<string, unknown> }) => row.values)).toEqual([
    { ticket: 'A', status: 'Open' }, { ticket: 'B', status: 'Open' },
  ])
})
