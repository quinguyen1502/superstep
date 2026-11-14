import { expect, test, type Locator } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'

const provider = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}/ollama`

test('triages support tickets with Dataset views, clipboard and an Agent aggregate', async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.addInitScript(() => {
    localStorage.setItem('lang', 'en')
    localStorage.setItem('theme', 'light')
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const name = process.env.HANDBOOK_SHOTS ? 'Support tickets · Triage' : `Support tickets ${Date.now()}`
  const created = await page.request.post('/api/datasets', { headers, data: { name, columns: [
    { key: 'number', label: 'Ticket ID', kind: 'auto_number' },
    { key: 'subject', label: 'Subject', kind: 'text' },
    { key: 'team', label: 'Team', kind: 'select', options: ['Support', 'Infra'] },
    { key: 'status', label: 'Status', kind: 'select', options: ['Open', 'Closed'] },
    { key: 'score', label: 'Priority', kind: 'number', validation_rules: { min: 1, max: 5, integer: true } },
    { key: 'link', label: 'Reference', kind: 'url' },
  ] } })
  expect(created.ok(), await created.text()).toBeTruthy()
  const { id: datasetId } = (await created.json()).data
  const base = `/api/datasets/${datasetId}`
  const tickets = [
    { subject: 'Printer jam', team: 'Support', status: 'Open', score: 2, link: 'https://example.org/tickets/printer' },
    { subject: 'VPN access', team: 'Infra', status: 'Open', score: 3 },
    { subject: 'Badge request', team: 'Support', status: 'Open', score: 1 },
    { subject: 'Keyboard replacement', team: 'Support', status: 'Closed', score: 5 },
  ]
  for (const values of tickets) expect((await page.request.post(`${base}/rows`, { headers, data: { values } })).ok()).toBeTruthy()
  await page.goto(`/datasets/${datasetId}`)
  const rows = page.getByTestId('dataset-row')
  await expect(rows).toHaveCount(4)
  const printer = rows.filter({ hasText: 'Printer jam' })
  await expect(printer.getByRole('link', { name: 'Open Reference in a new tab' })).toHaveAttribute('href', tickets[0].link!)
  const ticketId = printer.getByRole('button', { name: 'Ticket ID: 1' })
  await ticketId.dblclick()
  await expect(printer.getByRole('spinbutton', { name: 'Ticket ID' })).toHaveCount(0)

  await printer.getByRole('button', { name: 'Edit Priority: 2' }).dblclick()
  const priority = printer.getByRole('spinbutton', { name: 'Priority' })
  await priority.fill('9')
  await priority.press('Enter')
  await expect(page.getByRole('alert')).toContainText('Value violates the validation rules')
  await priority.press('Escape')
  await printer.getByRole('button', { name: 'Edit Priority: 2' }).click()
  await page.evaluate(() => {
    const transfer = new DataTransfer()
    transfer.setData('text/plain', '4\n5')
    document.activeElement?.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: transfer }))
  })
  await expect(rows.nth(1).getByRole('button', { name: 'Edit Priority: 5' })).toBeVisible()
  await printer.getByRole('button', { name: 'Edit Priority: 4' }).click()
  await page.keyboard.press('Shift+ArrowDown')
  await page.keyboard.press('Control+d')
  await expect(rows.nth(1).getByRole('button', { name: 'Edit Priority: 4' })).toBeVisible()

  const choose = async (combobox: Locator, option: string) => {
    await combobox.click()
    await page.getByRole('option', { name: option, exact: true }).click()
  }
  await page.getByRole('button', { name: 'Filter', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Filter', exact: true })
  const statusRule = dialog.getByRole('group', { name: 'Condition 1', exact: true })
  await choose(statusRule.getByRole('combobox', { name: 'Filter column' }), 'Status')
  await choose(statusRule.getByRole('combobox', { name: 'Filter value' }), 'Open')
  await dialog.getByRole('button', { name: 'Add group' }).click()
  const group = dialog.getByRole('group', { name: 'Group 2', exact: true })
  await choose(group.getByRole('combobox', { name: 'Match conditions in group 2' }), 'Match any (OR)')
  const priorityRule = group.getByRole('group', { name: 'Condition 2.1', exact: true })
  await choose(priorityRule.getByRole('combobox', { name: 'Filter column' }), 'Priority')
  await priorityRule.getByRole('spinbutton', { name: 'Filter value' }).fill('4')
  await group.getByRole('button', { name: 'Add condition' }).click()
  const otherPriority = group.getByRole('group', { name: 'Condition 2.2', exact: true })
  await choose(otherPriority.getByRole('combobox', { name: 'Filter column' }), 'Priority')
  await otherPriority.getByRole('spinbutton', { name: 'Filter value' }).fill('5')
  await dialog.getByRole('button', { name: 'Apply filters' }).click()
  await expect(rows).toHaveCount(2)
  await page.getByRole('button', { name: 'Summary', exact: true }).click()
  await choose(page.getByRole('combobox', { name: 'Summary for Priority' }), 'Sum')
  await expect(page.getByRole('status', { name: 'Summary for Priority' })).toHaveText('8')
  await choose(page.getByRole('combobox', { name: 'Group by' }), 'Team')
  await expect(page.getByRole('button', { name: 'Infra 1 row', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Support 1 row', exact: true }).click()
  await expect(printer).toBeVisible()
  await page.mouse.move(2, 898)
  if (process.env.HANDBOOK_SHOTS) {
    await page.screenshot({ path: '../handbook/docs/en/images/datasets-triage.png' })
    await page.evaluate(() => document.documentElement.classList.add('dark'))
    await page.screenshot({ path: '../handbook/docs/en/images/datasets-triage-dark.png' })
    await page.locator('#lang-switch').click()
    await page.locator('[data-lang=vi]').click()
    await expect(page.getByRole('combobox', { name: 'Nhóm theo' })).toBeVisible()
    await page.mouse.move(2, 898)
    await page.getByRole('heading', { name, exact: true }).click()
    await page.mouse.move(2, 898)
    await page.screenshot({ path: '../handbook/docs/vi/images/datasets-triage-dark.png' })
    await page.evaluate(() => document.documentElement.classList.remove('dark'))
    await page.screenshot({ path: '../handbook/docs/vi/images/datasets-triage.png' })
    await page.locator('#lang-switch').click()
    await page.locator('[data-lang=en]').click()
    await expect(page.getByRole('combobox', { name: 'Group by' })).toBeVisible()
  } else {
    await info.attach('ticket-triage', { body: await page.screenshot(), contentType: 'image/png' })
  }

  const credential = await page.request.post('/api/credentials', { headers, data: {
    name, provider: 'ollama', base_url: provider,
  } })
  expect(credential.ok()).toBeTruthy()
  const { id: credentialId } = (await credential.json()).data
  const workflowId = await newWorkflow(page, headers, {
    name,
    state: [{ name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 40), N('agent', 'agent', 290, {
      prompt: 'What is the total priority for open tickets with priority 4 or 5, grouped by team?', output_field: 'answer',
      credential_id: credentialId, model: 'llama3.2:latest', tools: [{
        name: 'summarize_tickets', source: 'dataset', dataset_id: datasetId, operations: ['aggregate_rows'],
        fields: ['team', 'status', 'score'], filter_ops: { status: ['eq'], score: ['eq'] },
      }],
    }), N('end', 'end', 540)],
    edges: [{ id: 'a', source: 'start', target: 'agent' }, { id: 'b', source: 'agent', target: 'end' }],
  })
  const grant = await page.request.put(`${base}/access/grants/${workflowId}`, { headers, data: { permission: 'read' } })
  expect(grant.ok()).toBeTruthy()
  await page.goto(`/workflows/${workflowId}`)
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(page.locator('.trace-row').filter({ hasText: '2 aggregate groups' })).toBeVisible()
  await expect(page.getByTestId('span-agent').filter({ hasText: 'The total priority is 8 across 2 teams.' })).toBeVisible()
})
