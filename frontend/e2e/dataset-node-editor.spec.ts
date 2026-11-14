import { expect, test, type Locator, type Page } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'
import { expectRowAligned } from './helpers/alignment'
import { literally, vt } from './catalog'

async function pick(page: Page, trigger: Locator, name: string) {
  await trigger.click()
  await page.getByRole('option', { name, exact: true }).click()
}

test('Dataset node configures lookup and upsert, simulates tests and rebinds templates', async ({ page }, info) => {
  await page.addInitScript(() => {
    localStorage.setItem('lang', 'en')
    if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light')
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const ticket = { key: 'ticket', label: 'Ticket', kind: 'text', required: true, unique: true }
  const datasetName = `Dataset node records ${Date.now()}`
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: datasetName, columns: [ticket, { key: 'subject', label: 'Subject', kind: 'text' }],
  } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const base = `/api/datasets/${dataset.id}`
  const wid = await newWorkflow(page, headers, {
    name: `Dataset node workflow ${Date.now()}`, state: [{ name: 'result', type: 'object' }],
    nodes: [N('s', 'start', 40), N('data', 'dataset', 290, { label: 'Records', operation: 'find_rows' }), N('e', 'end', 540)],
    edges: [{ id: 'a', source: 's', target: 'data' }, { id: 'b', source: 'data', target: 'e' }],
  })
  const settings = async () => {
    await page.locator('.react-flow__node[data-id="data"]').click()
    await page.locator('#config-tab-settings').click()
  }
  const dataTab = page.locator('#config-tab-data')
  const returned = page.getByRole('group', { name: 'Fields to return' })
  const rows = async () => {
    const response = await page.request.post(`${base}/rows/query`, { headers, data: {} })
    expect(response.ok()).toBeTruthy()
    return (await response.json()).data.items
  }
  const savedConfig = async () => {
    const response = await page.request.get(`/api/workflows/${wid}`, { headers })
    expect(response.ok()).toBeTruthy()
    return (await response.json()).data.nodes.find((node: { id: string }) => node.id === 'data').data
  }
  const save = async () => {
    await page.locator('#save-btn').click()
    await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  }

  await page.goto(`/workflows/${wid}`)
  await expect(page.getByTestId('palette-card').and(page.locator('[data-type=dataset]'))).toBeVisible()
  await settings()
  const datasetPicker = page.getByRole('combobox', { name: 'Dataset', exact: true })
  await pick(page, datasetPicker, datasetName)
  const readHint = page.getByText('Grant this workflow read access', { exact: false })
  await expect(readHint).toBeVisible()
  const grant = await page.request.put(`${base}/access/grants/${wid}`, { headers, data: { permission: 'read_write' } })
  expect(grant.ok()).toBeTruthy()
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(readHint).toHaveCount(0)

  await dataTab.click()
  await expect(page.getByRole('spinbutton', { name: 'Maximum rows' })).toBeVisible()
  await page.getByRole('button', { name: 'Add condition' }).click()
  const condition = page.getByRole('group', { name: 'Condition 1' })
  await expectRowAligned([condition.getByRole('combobox', { name: 'Filter column' }), condition.getByRole('button', { name: 'Remove condition' })], { label: 'Dataset condition controls' })
  await expect(condition.getByText('Matches the exact value, letter case included.')).toBeVisible()
  await condition.getByRole('textbox', { name: 'Filter value' }).fill('T-01')
  await returned.getByRole('checkbox', { name: 'Ticket', exact: true }).check()
  await pick(page, page.getByRole('combobox', { name: 'Output field' }), 'result')
  await save()
  expect(await savedConfig()).toMatchObject({ dataset_id: dataset.id, operation: 'find_rows', fields: ['ticket'], output_field: 'result', arguments: { filters: [{ field: 'ticket', op: 'eq', value: 'T-01' }] } })

  await page.getByRole('button', { name: 'Add group' }).click()
  const nested = page.getByRole('group', { name: 'Group 2', exact: true })
  await pick(page, nested.getByRole('combobox', { name: 'Match conditions in group 2' }), 'Match any (OR)')
  await pick(page, nested.getByRole('combobox', { name: 'Filter operator' }), 'Is one of')
  await expect(nested.getByRole('status')).toHaveText('Enter a value for each input.')
  await nested.getByRole('textbox', { name: 'Value 1', exact: true }).fill('T-02')
  await nested.getByRole('button', { name: 'Add value' }).click()
  await nested.getByRole('textbox', { name: 'Value 2', exact: true }).fill('T-03')
  await expect(nested.getByRole('status')).toHaveCount(0)
  await save()
  const grouped = {
    type: 'group', conjunction: 'and', children: [
      { type: 'rule', field: 'ticket', op: 'eq', value: 'T-01' },
      { type: 'group', conjunction: 'or', children: [
        { type: 'rule', field: 'ticket', op: 'in', value: ['T-02', 'T-03'] },
      ] },
    ],
  }
  const savedArguments = (await savedConfig()).arguments
  expect(savedArguments.filter_tree).toEqual(grouped)
  expect(savedArguments.filters).toBeUndefined()
  await page.reload()
  await settings()
  await dataTab.click()
  await expect(nested.getByRole('textbox', { name: 'Value 2', exact: true })).toHaveValue('T-03')

  await page.locator('#config-tab-settings').click()
  await pick(page, page.getByRole('combobox', { name: 'Operation' }), 'Upsert row')
  await dataTab.click()
  await pick(page, page.getByRole('combobox', { name: 'Unique match field' }), 'Ticket')
  await page.getByRole('group', { name: 'Fields to write' }).getByRole('textbox', { name: 'Ticket', exact: true }).fill('T-01')
  await page.screenshot({ path: info.outputPath('dataset-node-light.png') })
  await save()
  expect(await savedConfig()).toMatchObject({ operation: 'upsert_row', arguments: { key: 'ticket', values: { ticket: 'T-01' } } })

  await page.locator('#tests-tab').click()
  await page.locator('#tests-add').click()
  await page.locator('#test-name').fill('Dataset write simulation')
  await page.locator('#test-save').click()
  await page.locator('#tests-run-all').click()
  await page.getByTestId('result-open-run').click()
  await expect(page.getByTestId('span-dataset-dry-run')).toBeVisible()
  expect(await rows()).toEqual([])

  await page.locator('#run-btn').click()
  await page.getByRole('alertdialog', { name: 'This run can change Dataset rows' }).getByRole('button', { name: 'Run', exact: true }).click()
  await expect.poll(async () => (await rows()).map((row: { values: unknown }) => row.values)).toEqual([{ ticket: 'T-01', subject: null }])
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok')
  await expect(page.getByTestId('span-dataset-dry-run')).toHaveCount(0)

  const template = await page.request.post('/api/templates', { headers, data: { workflow_id: wid, name: 'Dataset rebind template' } })
  expect(template.ok()).toBeTruthy()
  const { id: tid } = (await template.json()).data
  const exported = await page.request.get(`/api/templates/${tid}/export`, { headers })
  expect(exported.ok()).toBeTruthy()
  expect(await exported.text()).not.toContain(dataset.id)
  const used = await page.request.post(`/api/templates/${tid}/use`, { headers })
  expect(used.ok()).toBeTruthy()
  const copy = (await used.json()).data
  await page.evaluate(() => localStorage.setItem('theme', 'dark'))
  await page.goto(`/workflows/${copy.id}`)
  await settings()
  await expect(page.getByText('Imported templates need a local binding.', { exact: false })).toBeVisible()
  const renamed = await page.request.put(`${base}/columns/ticket`, { headers, data: {
    revision: dataset.revision, column: { ...ticket, label: 'Ticket number' },
  } })
  expect(renamed.ok()).toBeTruthy()
  await pick(page, datasetPicker, datasetName)
  await expect(page.getByText('Grant this workflow write access', { exact: false })).toBeVisible()
  await dataTab.click()
  await expect(returned.getByRole('checkbox', { name: 'Ticket number', exact: true })).toBeChecked()
  await expect(page.getByRole('group', { name: 'Fields to write' }).getByRole('textbox', { name: 'Ticket number', exact: true })).toHaveValue('T-01')
  await page.screenshot({ path: info.outputPath('dataset-node-dark.png') })

  const alternate = await page.request.post('/api/datasets', { headers, data: { name: 'Dataset without a unique field',
    columns: [{ key: 'other', label: 'Other', kind: 'text' }],
  } })
  expect(alternate.ok()).toBeTruthy()
  await page.locator('#config-tab-settings').click()
  await pick(page, datasetPicker, 'Dataset without a unique field')
  await dataTab.click()
  await expect(page.getByText('Upsert needs a column with the Unique constraint.')).toBeVisible()
  await expect(page.getByText('These fields are missing from the selected dataset: ticket.')).toBeVisible()
  await page.getByRole('button', { name: 'Remove missing mappings' }).click()
  await expect(page.getByText('These fields are missing', { exact: false })).toHaveCount(0)
})

test('Dataset node configures Delete row by unique field or row ID and needs the delete capability', async ({ page }) => {
  await page.addInitScript(() => {
    if (!localStorage.getItem('lang')) localStorage.setItem('lang', 'en')
    localStorage.setItem('theme', 'light')
  })
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const datasetName = `Dataset delete records ${Date.now()}`
  const created = await page.request.post('/api/datasets', { headers, data: { name: datasetName, columns: [
    { key: 'ticket', label: 'Ticket', kind: 'text', required: true, unique: true },
    { key: 'subject', label: 'Subject', kind: 'text' },
  ] } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const base = `/api/datasets/${dataset.id}`
  const seeded = await page.request.post(`${base}/rows`, { headers, data: { values: { ticket: 'T-09', subject: 'Close me' } } })
  expect(seeded.ok()).toBeTruthy()
  const wid = await newWorkflow(page, headers, {
    name: `Dataset delete workflow ${Date.now()}`, state: [{ name: 'result', type: 'object' }],
    nodes: [N('s', 'start', 40), N('data', 'dataset', 290, { label: 'Records', operation: 'find_rows' }), N('e', 'end', 540)],
    edges: [{ id: 'a', source: 's', target: 'data' }, { id: 'b', source: 'data', target: 'e' }],
  })
  const tickets = async () => {
    const response = await page.request.post(`${base}/rows/query`, { headers, data: {} })
    expect(response.ok()).toBeTruthy()
    return (await response.json()).data.items.map((row: { values: { ticket: string } }) => row.values.ticket)
  }
  const savedConfig = async () => {
    const response = await page.request.get(`/api/workflows/${wid}`, { headers })
    expect(response.ok()).toBeTruthy()
    return (await response.json()).data.nodes.find((node: { id: string }) => node.id === 'data').data
  }
  const save = async () => {
    await page.locator('#save-btn').click()
    await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  }
  const grant = async (allow_delete: boolean) => {
    const response = await page.request.put(`${base}/access/grants/${wid}`, { headers, data: { permission: 'read_write', allow_delete } })
    expect(response.ok()).toBeTruthy()
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  }
  const dataTab = page.locator('#config-tab-data')

  await grant(false)
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="data"]').click()
  await page.locator('#config-tab-settings').click()
  await pick(page, page.getByRole('combobox', { name: 'Dataset', exact: true }), datasetName)
  await pick(page, page.getByRole('combobox', { name: 'Operation' }), 'Delete row')
  const deleteHint = page.getByText('Turn on Allow row deletion for this workflow', { exact: false })
  await expect(deleteHint).toBeVisible()

  await dataTab.click()
  await expect(page.getByText('Choose the row to delete', { exact: false })).toBeVisible()
  await expect(page.getByRole('group', { name: 'Fields to return' })).toHaveCount(0)
  await pick(page, page.getByRole('combobox', { name: 'Delete by' }), 'Unique field')
  const keyPicker = page.getByRole('combobox', { name: 'Unique field to match' })
  await keyPicker.click()
  await expect(page.getByRole('option', { name: 'Subject', exact: true })).toHaveCount(0)
  await page.getByRole('option', { name: 'Ticket', exact: true }).click()
  await page.getByRole('textbox', { name: 'Value of Ticket', exact: true }).fill('T-09')
  await expect(page.getByText('Choose the row to delete', { exact: false })).toHaveCount(0)
  await pick(page, page.getByRole('combobox', { name: 'Output field' }), 'result')
  await save()
  expect(await savedConfig()).toMatchObject({ dataset_id: dataset.id, operation: 'delete_row', fields: ['ticket'],
    output_field: 'result', arguments: { key: 'ticket', value: 'T-09' } })
  expect(Object.keys((await savedConfig()).arguments).sort()).toEqual(['key', 'value'])

  await page.locator('#run-btn').click()
  await page.getByRole('alertdialog', { name: 'This run can change Dataset rows' }).getByRole('button', { name: 'Run', exact: true }).click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'error', { timeout: 30_000 })
  expect(await tickets()).toEqual(['T-09'])

  await grant(true)
  await page.locator('#config-tab-settings').click()
  await expect(deleteHint).toHaveCount(0)
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect.poll(tickets).toEqual([])

  await page.evaluate(() => localStorage.setItem('lang', 'vi'))
  await page.reload()
  await page.locator('.react-flow__node[data-id="data"]').click()
  await dataTab.click()
  const mode = page.getByRole('combobox', { name: vt('datasetNode.deleteBy') })
  await mode.focus()
  await page.keyboard.press('Enter')
  const rowOption = page.getByRole('option', { name: vt('datasetNode.deleteModes.row_id'), exact: true })
  await expect(page.getByRole('option', { name: vt('datasetNode.deleteModes.key'), exact: true })).toBeFocused()
  await page.keyboard.press('ArrowUp')
  await expect(rowOption).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(mode).toHaveText(vt('datasetNode.deleteModes.row_id'))
  await expect(page.getByText(vt('datasetNode.deleteTargetMissing'))).toBeVisible()
  const rowLabel = page.locator('label').filter({ hasText: new RegExp(`^${literally(vt('dataset.rowId')).source}$`) })
  const editor = page.locator(`[id="${await rowLabel.getAttribute('for')}"]`)
  await editor.focus()
  await page.keyboard.type('row-123')
  await expect(page.getByText(vt('datasetNode.deleteTargetMissing'))).toHaveCount(0)
  await save()
  expect((await savedConfig()).arguments).toEqual({ row_id: 'row-123' })
})
