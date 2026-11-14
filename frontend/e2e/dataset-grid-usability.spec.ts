import { expect, test } from '@playwright/test'
import { signIn } from './helpers'

test('keeps grid layout when reloaded and supports paged rows and deep-linked tabs', async ({ page }, info) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: 'Paged dataset',
    columns: [
      { key: 'ticket', label: 'Ticket', kind: 'text', unique: true },
      { key: 'note', label: 'Note', kind: 'text' },
      { key: 'score', label: 'Score', kind: 'number' },
    ],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const path = `/datasets/${dataset.id}`
  const imported = await page.request.post('/api/datasets/csv/import', { headers, data: {
    text: 'Ticket,Note,Score\n' + Array.from({ length: 60 }, (_, i) => `Ticket ${i},Note ${i},${i}`).join('\n'),
    dataset_id: dataset.id, schema_revision: dataset.revision, mapping: ['ticket', 'note', 'score'],
  } })
  expect(imported.ok()).toBeTruthy()

  await page.goto(path)
  await expect(page.getByText('1–50 of 60')).toBeVisible()
  await page.getByRole('combobox', { name: 'Rows per page' }).click()
  await page.getByRole('option', { name: '25', exact: true }).click()
  await expect(page.getByText('1–25 of 60')).toBeVisible()
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByText('26–50 of 60')).toBeVisible()

  const resize = page.getByRole('separator', { name: /Ticket/ })
  await resize.focus()
  await resize.press('ArrowRight')
  const size = await resize.getAttribute('aria-valuenow')
  await page.evaluate(({ id, width }) => localStorage.setItem(`studio-dataset-layout:${id}`, JSON.stringify({
    order: ['score', 'ticket', 'note'], sizes: { ticket: Number(width) }, visibility: { note: false },
  })), { id: dataset.id, width: size })
  await page.reload()
  await expect(page.getByRole('columnheader', { name: 'Score' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Note' })).toHaveCount(0)
  await expect(resize).toHaveAttribute('aria-valuenow', size!)
  await expect(page.getByRole('columnheader').nth(1)).toContainText('Score')

  await page.getByRole('tab', { name: 'Schema' }).click()
  await expect(page).toHaveURL(/tab=schema/)
  await expect(page.getByRole('tabpanel', { name: 'Schema' })).toBeVisible()
  await page.goto(`${path}?tab=access`)
  await expect(page.getByRole('tabpanel', { name: 'Access' })).toContainText('No workflow grants.')
  for (const theme of ['light', 'dark']) {
    await page.evaluate(active => document.documentElement.classList.toggle('dark', active === 'dark'), theme)
    await info.attach(`dataset-access-${theme}`, { body: await page.screenshot(), contentType: 'image/png' })
  }
})
