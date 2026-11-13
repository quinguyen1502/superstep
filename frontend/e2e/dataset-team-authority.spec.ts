import { expect, test } from '@playwright/test'
import { signIn } from './helpers'

test('team members edit rows while only the owner or an admin manages the dataset', async ({ page, browser }) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const stamp = Date.now().toString(36)
  const email = `peer-${stamp}@example.com`
  const context = await browser.newContext()  // registering signs in, so the member gets its own browser context
  const peer = await context.newPage()
  expect((await peer.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  const team = (await (await page.request.post('/api/teams', { headers, data: { name: `Authority ${stamp}` } })).json()).data
  for (const member of ['admin@example.com', email]) {
    expect((await page.request.post(`/api/teams/${team.id}/members`, { headers, data: { email: member } })).ok()).toBeTruthy()
  }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: `Managed ${stamp}`, team_id: team.id, columns: [{ key: 'ticket', label: 'Ticket', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data

  await peer.addInitScript(() => localStorage.setItem('lang', 'en'))
  await peer.goto('/login')
  await signIn(peer, email, 'secret12')
  await peer.goto(`/datasets/${dataset.id}`)
  const note = 'Only the dataset owner or an admin can edit this dataset'
  await peer.getByRole('button', { name: 'Dataset actions' }).click()
  for (const name of ['Edit dataset', 'Access', 'Delete dataset']) {
    await expect(peer.getByRole('menuitem', { name, exact: true })).toBeDisabled()
  }
  await expect(peer.getByRole('menuitem', { name: 'Import CSV', exact: true })).toBeEnabled()
  await expect(peer.getByRole('menuitem', { name: 'Transfer ownership' })).toHaveCount(0)
  await expect(peer.getByText(note, { exact: false })).toBeVisible()
  await peer.getByRole('menuitem', { name: 'View schema' }).click()
  const schema = peer.getByRole('dialog', { name: 'Schema' })
  await expect(schema.getByRole('button', { name: 'Add column' })).toBeDisabled()
  await expect(schema.getByText(note, { exact: false })).toBeVisible()
  await schema.getByRole('button', { name: 'Close' }).click()
  await expect(peer.getByRole('button', { name: 'Add row' })).toBeEnabled()

  await page.goto(`/datasets/${dataset.id}`)
  await page.getByRole('button', { name: 'Dataset actions' }).click()
  await expect(page.getByRole('menuitem', { name: 'Edit dataset', exact: true })).toBeEnabled()
  await expect(page.getByText(note, { exact: false })).toHaveCount(0)
  await page.getByRole('menuitem', { name: 'Transfer ownership' }).click()
  const transfer = page.getByRole('dialog', { name: 'Transfer ownership' })
  await expect(transfer.getByText('Current owner: admin@example.com')).toBeVisible()
  await transfer.getByRole('combobox', { name: 'New owner' }).click()
  await page.getByRole('option', { name: email }).click()
  await transfer.getByRole('button', { name: 'Transfer' }).click()
  await expect(transfer).toBeHidden()

  await peer.reload()
  await peer.getByRole('button', { name: 'Dataset actions' }).click()
  await expect(peer.getByRole('menuitem', { name: 'Edit dataset', exact: true })).toBeEnabled()
  await expect(peer.getByText(note, { exact: false })).toHaveCount(0)
  await context.close()
})
