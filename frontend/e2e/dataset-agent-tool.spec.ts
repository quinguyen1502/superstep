import { expect, test } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'

test('Agent Dataset tool configures projected fields and shows only the count in its trace', async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.addInitScript(() => {
    localStorage.setItem('lang', 'en')
    if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light')
    localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 240, right: 440, bottom: 260 }))
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const name = `Agent records ${Date.now()}`
  const response = await page.request.post('/api/datasets', { headers, data: { name, columns: [
    { key: 'ticket', label: 'Ticket', kind: 'text' }, { key: 'private_note', label: 'Private note', kind: 'text' },
  ] } })
  expect(response.ok()).toBeTruthy()
  const { id: did } = (await response.json()).data
  const base = `/api/datasets/${did}`
  const inserted = await page.request.post(`${base}/rows`, { headers, data: { values: {
    ticket: 'VISIBLE-TICKET', private_note: 'PRIVATE-ROW-VALUE',
  } } })
  expect(inserted.ok()).toBeTruthy()
  const wid = await newWorkflow(page, headers, { name,
    state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 40), N('ag', 'agent', 290, { prompt: '{{state.message}}', output_field: 'answer' }), N('end', 'end', 540)],
    edges: [{ id: 'a', source: 'start', target: 'ag' }, { id: 'b', source: 'ag', target: 'end' }],
  })
  const openSettings = async () => {
    await page.locator('.react-flow__node[data-id="ag"]').click()
    await page.locator('#config-tab-settings').click()
  }
  await page.goto(`/workflows/${wid}`)
  await openSettings()
  await page.locator('#agent-add-tool').click()
  await page.getByRole('menuitem', { name: 'Dataset', exact: true }).click()
  const tool = page.getByTestId('agent-tool').and(page.locator('[data-source=dataset]'))
  await tool.getByRole('combobox', { name: 'Dataset', exact: true }).click()
  await page.getByRole('option', { name, exact: true }).click()
  await expect(tool.getByText('Grant this workflow read access', { exact: false })).toBeVisible()
  const grant = await page.request.put(`${base}/access/grants/${wid}`, { headers, data: { permission: 'read' } })
  expect(grant.ok()).toBeTruthy()
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(tool.getByText('Grant this workflow read access', { exact: false })).toHaveCount(0)
  await tool.getByRole('checkbox', { name: 'Ticket', exact: true }).check()
  await tool.getByRole('button', { name: 'Allowed operators for Ticket', exact: true }).click()
  await page.getByRole('menuitemcheckbox', { name: 'Equals', exact: true }).click()
  await expect(page.getByRole('menuitemcheckbox', { name: 'Equals', exact: true })).toBeChecked()
  await page.keyboard.press('Escape')
  await tool.getByRole('spinbutton', { name: 'Maximum rows' }).fill('2')
  await tool.getByRole('group', { name: 'Allowed filter operators' }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('dataset-agent-light.png') })
  await page.locator('#save-btn').click()
  await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data
  expect(saved.nodes.find((node: { id: string }) => node.id === 'ag').data.tools).toMatchObject([
    { source: 'dataset', dataset_id: did, fields: ['ticket'], filter_ops: { ticket: ['eq'] }, limit: 2 },
  ])
  await page.evaluate(() => localStorage.setItem('theme', 'dark'))
  await page.reload()
  await openSettings()
  await tool.getByRole('group', { name: 'Allowed filter operators' }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('dataset-agent-dark.png') })

  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok')
  const span = page.locator('.trace-row').filter({ hasText: 'find_dataset_rows returned 1 row' })
  await expect(span).toBeVisible()
  await expect(span).not.toContainText('VISIBLE-TICKET')
  await span.click()
  await page.locator('#trace-detail').getByRole('tab', { name: 'Output' }).click()
  await expect(page.locator('#trace-detail')).not.toContainText(/VISIBLE-TICKET|PRIVATE-ROW-VALUE/)
})

test('Agent Dataset tool upserts only its configured fields and the row appears in Studio', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.addInitScript(() => {
    localStorage.setItem('lang', 'en')
    localStorage.setItem('theme', 'light')
    localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 240, right: 440, bottom: 260 }))
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const name = `Agent tickets ${Date.now()}`
  const response = await page.request.post('/api/datasets', { headers, data: { name, columns: [
    { key: 'ticket', label: 'Ticket', kind: 'text', unique: true, required: true },
    { key: 'subject', label: 'Subject', kind: 'text' }, { key: 'owner_note', label: 'Owner note', kind: 'text' },
  ] } })
  expect(response.ok()).toBeTruthy()
  const { id: did } = (await response.json()).data
  const base = `/api/datasets/${did}`
  const ticket = `TICKET-${Date.now()}`
  const wid = await newWorkflow(page, headers, { name,
    state: [{ name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 40), N('ag', 'agent', 290, { prompt: ticket, output_field: 'answer' }), N('end', 'end', 540)],
    edges: [{ id: 'a', source: 'start', target: 'ag' }, { id: 'b', source: 'ag', target: 'end' }],
  })
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ag"]').click()
  await page.locator('#config-tab-settings').click()
  await page.locator('#agent-add-tool').click()
  await page.getByRole('menuitem', { name: 'Dataset', exact: true }).click()
  const tool = page.getByTestId('agent-tool').and(page.locator('[data-source=dataset]'))
  await tool.getByRole('combobox', { name: 'Dataset', exact: true }).click()
  await page.getByRole('option', { name, exact: true }).click()
  const operations = tool.getByRole('group', { name: 'Operations the Agent can use' })
  await expect(operations.getByRole('checkbox', { name: 'Find rows', exact: true })).toBeDisabled()
  await expect(tool.getByText('Find rows with read-only access.', { exact: false })).toBeVisible()
  await expect(operations.getByRole('checkbox', { name: 'Delete row', exact: true })).toHaveCount(0)
  await operations.getByRole('checkbox', { name: 'Upsert row', exact: true }).check()
  await operations.getByRole('checkbox', { name: 'Find rows', exact: true }).uncheck()
  await expect(tool.getByText('An Agent cannot delete rows.', { exact: false })).toBeVisible()
  await expect(tool.getByText('Grant this workflow write access', { exact: false })).toBeVisible()
  await expect(tool.getByRole('group', { name: 'Allowed filter operators' })).toHaveCount(0)
  await tool.getByRole('combobox', { name: 'Unique match field' }).click()
  await expect(page.getByRole('option', { name: 'Subject', exact: true })).toHaveCount(0)
  await page.getByRole('option', { name: 'Ticket', exact: true }).click()
  const writable = tool.getByRole('group', { name: 'Fields the Agent can write' })
  await expect(writable.getByRole('checkbox', { name: 'Ticket', exact: true })).toBeChecked()
  await expect(writable.getByRole('checkbox', { name: 'Ticket', exact: true })).toBeDisabled()
  await writable.getByRole('checkbox', { name: 'Subject', exact: true }).check()
  await tool.getByRole('group', { name: 'Fields to return' }).getByRole('checkbox', { name: 'Ticket', exact: true }).check()
  const grant = await page.request.put(`${base}/access/grants/${wid}`, { headers, data: { permission: 'write' } })
  expect(grant.ok()).toBeTruthy()
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(tool.getByText('Grant this workflow write access', { exact: false })).toHaveCount(0)
  await page.locator('#save-btn').click()
  await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data
  expect(saved.nodes.find((node: { id: string }) => node.id === 'ag').data.tools).toMatchObject([
    { source: 'dataset', dataset_id: did, operations: ['upsert_row'], key: 'ticket', write_fields: ['ticket', 'subject'], fields: ['ticket'] },
  ])

  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  const span = page.locator('.trace-row').filter({ hasText: 'upserted 1 row' })
  await expect(span).toBeVisible()
  await span.click()
  await page.locator('#trace-detail').getByRole('tab', { name: 'Output' }).click()
  await expect(page.locator('#trace-detail')).not.toContainText(ticket)
  const rows = await page.request.post(`${base}/rows/query`, { headers, data: {} })
  expect((await rows.json()).data.items.map((row: { values: unknown }) => row.values)).toEqual([
    { ticket, subject: ticket, owner_note: null },
  ])
  await page.goto(`/datasets/${did}`)
  await expect(page.getByTestId('dataset-row').filter({ hasText: ticket })).toHaveCount(1)
})
