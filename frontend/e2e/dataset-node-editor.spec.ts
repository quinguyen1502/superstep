import { expect, test, type Locator, type Page } from '@playwright/test'
import { N, newWorkflow, signIn } from './helpers'
import { expectRowAligned } from './helpers/alignment'

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
  await condition.getByRole('textbox', { name: 'Filter value' }).fill('T-01')
  await returned.getByRole('checkbox', { name: 'Ticket', exact: true }).check()
  await pick(page, page.getByRole('combobox', { name: 'Output field' }), 'result')
  await save()
  expect(await savedConfig()).toMatchObject({ dataset_id: dataset.id, operation: 'find_rows', fields: ['ticket'], output_field: 'result', arguments: { filters: [{ field: 'ticket', op: 'eq', value: 'T-01' }] } })

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
