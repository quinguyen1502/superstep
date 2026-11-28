import { expect, test, type Page } from '@playwright/test'
import { join } from 'node:path'
import { DatasetClient } from '../../sdk/typescript/src/dataset'
import { vt } from './catalog'
import { signIn } from './helpers'
import { expectRowAligned } from './helpers/alignment'

const publicApi = '/api/public/v1/dataset-view'
const columns = [
  { key: 'subject', label: 'Subject', kind: 'text', unique: true },
  { key: 'priority', label: 'Priority', kind: 'number' },
  { key: 'details', label: 'Details', kind: 'long_text' },
  { key: 'state', label: 'State', kind: 'select', options: ['Open', 'Closed'] },
  { key: 'private_note', label: 'Private note', kind: 'text' },
] as const
const ticket = (index: number) => `Ticket ${String(index).padStart(2, '0')}`

async function owner(page: Page) {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  return { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
}

async function seedTickets(page: Page, count: number, name: string) {
  const headers = await owner(page)
  const created = await page.request.post('/api/datasets', { headers, data: { name, columns } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data as { id: string; revision: number }
  const path = `/datasets/${dataset.id}`
  const imported = await page.request.post('/api/datasets/csv/import', { headers, data: {
    dataset_id: dataset.id, schema_revision: dataset.revision, mapping: columns.map(column => column.key),
    text: 'Subject,Priority,Details,State,Private note\n' +
      Array.from({ length: count }, (_, index) => `${ticket(index)},${index},Public progress note,Open,secretmarker\n`).join('') +
      'Closed internal ticket,100,Private details,Closed,secretmarker\n',
  } })
  expect(imported.ok()).toBeTruthy()
  return { dataset, headers, path }
}

async function screenshot(page: Page, name: string) {
  const directory = process.env.DATASET_SHARE_QA_SCREENSHOTS
  if (directory) await page.screenshot({ path: join(directory, name), animations: 'disabled' })
}

test('shares a filtered preview with an anonymous visitor and disables replaced links', async ({ page, browser, context }) => {
  const { path } = await seedTickets(page, 52, 'Private support tickets')
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto(path)
  await page.getByRole('tab', { name: 'Access' }).click()
  await expect(page.getByRole('heading', { name: 'Share links' })).toBeVisible()
  const create = page.getByRole('button', { name: 'Create share link', exact: true })
  await create.press('Enter')
  const editor = page.getByRole('dialog', { name: 'Create share link' })
  const preview = editor.getByRole('button', { name: 'Preview', exact: true })
  await expect(preview).toBeDisabled()
  await editor.getByRole('textbox', { name: 'Link name' }).fill('Open support tickets')
  await editor.getByRole('checkbox', { name: 'Priority', exact: true }).press('Space')
  await editor.getByRole('checkbox', { name: 'Subject', exact: true }).check()
  await editor.getByRole('checkbox', { name: 'Details', exact: true }).check()
  await editor.getByRole('button', { name: 'Add condition' }).click()
  await editor.getByRole('combobox', { name: 'Filter column' }).click()
  await page.getByRole('option', { name: 'State', exact: true }).click()
  await expect(editor.getByRole('combobox', { name: 'Filter operator' })).toHaveText('Equals')
  await editor.getByRole('combobox', { name: 'Filter value' }).click()
  await page.getByRole('option', { name: 'Open', exact: true }).click()
  await preview.press('Enter')
  const previewTable = editor.getByRole('table', { name: 'Published rows' })
  await expect(previewTable.getByRole('columnheader')).toHaveText(['Priority', 'Subject', 'Details'])
  await expect(previewTable.getByRole('row')).toHaveCount(51)
  await editor.getByRole('button', { name: 'Edit view' }).press('Enter')
  await expect(editor.getByRole('textbox', { name: 'Link name' })).toBeFocused()
  await expect(editor.getByRole('combobox', { name: 'Filter value' })).toHaveText('Open')
  await preview.press('Enter')
  await expect(previewTable.getByRole('row')).toHaveCount(51)
  const previewRows = await previewTable.getByRole('row').allTextContents()
  await screenshot(page, 'share-preview-light.png')
  await editor.getByRole('button', { name: 'Create share link', exact: true }).click()
  const result = page.getByRole('dialog', { name: 'Public link' })
  const url = await result.getByRole('textbox', { name: 'Public link' }).inputValue()
  const link = new URL(url)
  expect(link.pathname).toBe('/dataset-view')
  expect(link.search).toBe('')
  expect(/^#dssh_[\w-]{43}$/.test(link.hash)).toBeTruthy()
  await result.getByRole('button', { name: 'Copy public link' }).click()
  await expect(result.getByRole('status')).toHaveText('Link copied.')
  expect(await page.evaluate(async expected => await navigator.clipboard.readText() === expected, url)).toBeTruthy()
  await result.getByRole('button', { name: 'Close', exact: true }).last().press('Enter')
  await expect(create).toBeFocused()
  await expect(page.getByRole('textbox', { name: 'Public link' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Fixed filter' }).click()
  await expect(page.getByRole('combobox', { name: 'Filter value' })).toHaveText('Open')
  await page.getByRole('button', { name: 'Fixed filter' }).click()

  const visitor = await browser.newContext({
    baseURL: link.origin, locale: 'en-US', colorScheme: 'dark', viewport: { width: 390, height: 740 },
  })
  try {
    const reader = await visitor.newPage()
    const request = reader.waitForRequest(req => new URL(req.url()).pathname === publicApi)
    await reader.goto(url)
    const sent = await request
    const headers = await sent.allHeaders()
    expect(headers['x-dataset-share'] === link.hash.slice(1)).toBeTruthy()
    expect(headers.cookie).toBeUndefined()
    expect(headers.referer || '').toBe('')
    expect(new URL(sent.url()).search).toBe('')
    await expect(reader.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex')
    await expect(reader.getByRole('heading', { name: 'Open support tickets' })).toBeVisible()
    const table = reader.getByRole('table', { name: 'Published rows' })
    await expect(table.getByRole('row')).toHaveText(previewRows)
    await expect(reader.getByText('Private note')).toHaveCount(0)
    await expect(reader.getByText('Closed internal ticket')).toHaveCount(0)
    await expect(reader.getByRole('button', { name: 'Add row' })).toHaveCount(0)
    const next = reader.getByRole('button', { name: 'Next page' })
    await next.press('Enter')
    await expect(table.getByRole('row')).toHaveCount(3)
    await expect(next).toBeFocused()
    await expect(next).toBeDisabled()
    await reader.getByRole('button', { name: 'Previous page' }).press('Enter')
    await expect(table.getByRole('row')).toHaveText(previewRows)
    const search = reader.getByRole('searchbox', { name: 'Search rows' })
    await expectRowAligned([search, reader.getByRole('button', { name: 'Search', exact: true })], { label: 'public Dataset search' })
    await search.fill('secretmarker')
    await search.press('Enter')
    await expect(reader.getByText('No rows match your search.')).toBeVisible()
    await search.fill(ticket(10))
    await search.press('Enter')
    await expect(table.getByRole('row')).toHaveCount(2)
    await expect(table.getByRole('cell', { name: ticket(10) })).toBeVisible()

    await expect(reader.locator('html')).toHaveClass(/dark/)
    await reader.getByRole('button', { name: 'Language', exact: true }).click()
    await reader.getByRole('menuitem', { name: vt('lang.vi') }).click()
    await expect(reader.getByText(vt('dataset.share.readOnly'))).toBeVisible()
    await expect(reader.getByRole('searchbox', { name: vt('dataset.searchRows') })).toBeVisible()
    expect(await reader.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
    await reader.getByRole('heading', { name: 'Open support tickets' }).click()
    await screenshot(reader, 'share-view-mobile-dark.png')
    await reader.locator('#theme-btn').click()
    await expect(reader.locator('html')).not.toHaveClass(/dark/)
    await reader.setViewportSize({ width: 1120, height: 800 })
    await reader.getByRole('heading', { name: 'Open support tickets' }).click()
    await screenshot(reader, 'share-view-desktop-light.png')

    await page.getByRole('button', { name: 'Rotate link for Open support tickets' }).click()
    await page.getByRole('dialog', { name: 'Rotate link' }).getByRole('button', { name: 'Rotate link' }).click()
    const replacement = await result.getByRole('textbox', { name: 'Public link' }).inputValue()
    expect(replacement !== url).toBeTruthy()
    await result.getByRole('button', { name: 'Close', exact: true }).last().click()
    await reader.getByRole('searchbox', { name: vt('dataset.searchRows') }).press('Enter')
    await expect(reader.getByRole('heading', { name: vt('dataset.share.unavailable') })).toBeVisible()
    await expect(reader.getByText(ticket(10))).toHaveCount(0)
    await reader.goto(replacement)
    await expect(reader.getByRole('heading', { name: 'Open support tickets' })).toBeVisible()

    await page.getByRole('button', { name: 'Revoke link for Open support tickets' }).click()
    const revoke = page.getByRole('alertdialog', { name: 'Revoke share link' })
    const submit = revoke.getByRole('button', { name: 'Revoke link', exact: true })
    await revoke.getByRole('textbox').fill('open support tickets')
    await expect(submit).toBeDisabled()
    await revoke.getByRole('textbox').fill('Open support tickets')
    await submit.press('Enter')
    await expect(page.getByText('Share link revoked.')).toBeVisible()
    await expect(page.getByText('No share links yet.')).toBeVisible()
    await reader.reload()
    await expect(reader.getByRole('heading', { name: vt('dataset.share.unavailable') })).toBeVisible()
  } finally {
    await visitor.close()
  }
})

test('a Connected SDK write refreshes two Studio sessions and appears in the public view on retry', async ({ page, browser, baseURL }) => {
  const { dataset, headers, path } = await seedTickets(page, 0, 'Connected support tickets')
  const issued = await page.request.post(`/api${path}/access/tokens`, {
    headers, data: { name: 'Support integration', permission: 'read_write' },
  })
  expect(issued.ok()).toBeTruthy()
  const { token } = (await issued.json()).data
  const share = await page.request.post(`/api${path}/shares`, { headers, data: {
    name: 'Public progress',
    fields: ['subject'],
    filter_tree: { type: 'group', conjunction: 'and', children: [{ type: 'rule', field: 'state', op: 'eq', value: 'Open' }] },
    schema_revision: dataset.revision,
  } })
  expect(share.ok()).toBeTruthy()
  const { token: shareToken } = (await share.json()).data
  const connection = new DatasetClient({
    baseUrl: baseURL!,
    datasetId: dataset.id,
    token,
    columns: columns.map(column => ({
      key: column.key,
      kind: column.kind,
      ...('unique' in column ? { unique: column.unique } : {}),
      ...('options' in column ? { options: [...column.options] } : {}),
    })),
  })

  const peer = await browser.newContext({ baseURL })
  const visitor = await browser.newContext({ baseURL, locale: 'en-US' })
  try {
    const studio = await peer.newPage()
    await owner(studio)
    const workbook = page.getByRole('table', { name: 'Grid view' })
    const peerWorkbook = studio.getByRole('table', { name: 'Grid view' })
    await Promise.all([page.goto(path), studio.goto(path)])
    await expect(workbook.getByText('Closed internal ticket')).toBeVisible()
    await expect(peerWorkbook.getByText('Closed internal ticket')).toBeVisible()

    const reader = await visitor.newPage()
    const copied = `/dataset-view#${shareToken}`
    let resume: () => void = () => {}
    const hold = new Promise<void>(resolve => { resume = resolve })
    const publicRows = (url: URL) => url.pathname === `${publicApi}/rows`
    await reader.route(publicRows, async route => {
      await hold
      await route.continue()
    })
    await reader.goto(copied)
    try {
      await expect(reader.getByRole('status')).toHaveText('Loading…')
    } finally {
      resume()
    }
    await expect(reader.getByText('There are no published rows.')).toBeVisible()
    await reader.unroute(publicRows)
    expect((await connection.findRows(['subject'], { search: 'Closed internal' })).items).toHaveLength(1)
    await connection.insertRow({
      subject: 'SDK status update', priority: 3, state: 'Open', private_note: 'Private SDK note',
    }, { fields: ['subject'] })
    await expect(workbook.getByText('SDK status update')).toBeVisible()
    await expect(peerWorkbook.getByText('SDK status update')).toBeVisible()
    await expect(reader.getByText('There are no published rows.')).toBeVisible()

    await reader.route(`**${publicApi}/rows?**`, route => route.abort(), { times: 1 })
    await reader.getByRole('searchbox', { name: 'Search rows' }).press('Enter')
    await expect(reader.getByRole('alert')).toBeVisible()
    await reader.getByRole('button', { name: 'Retry' }).press('Enter')
    const table = reader.getByRole('table', { name: 'Published rows' })
    await expect(table.getByRole('cell', { name: 'SDK status update' })).toBeVisible()
    await expect(table.getByRole('row')).toHaveCount(2)
    await expect(reader.getByText('Private SDK note')).toHaveCount(0)
  } finally {
    await peer.close()
    await visitor.close()
  }
})
