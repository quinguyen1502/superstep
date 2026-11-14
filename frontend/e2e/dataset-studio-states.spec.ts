import { expect, test, type Page, type TestInfo } from '@playwright/test'
import en from '../src/locales/en.json' with { type: 'json' }
import vi from '../src/locales/vi.json' with { type: 'json' }
import { signIn } from './helpers'

// Dataset Studio states: empty catalog, missing dataset, view-only access, row delete naming and the CSV issue list.
// Every state is checked and captured in English and Vietnamese, light and dark.
type Tree = { [key: string]: string | Tree }
type Lang = 'en' | 'vi'
const CATALOGS: Record<Lang, Tree> = { en: en as Tree, vi: vi as Tree }
const VARIANTS = [['en', 'light'], ['en', 'dark'], ['vi', 'light'], ['vi', 'dark']] as const

function tx(lang: Lang, key: string, vars: Record<string, string | number> = {}) {
  const value = key.split('.').reduce<string | Tree | undefined>((node, part) => (node && typeof node === 'object' ? node[part] : undefined), CATALOGS[lang])
  if (typeof value !== 'string') throw new Error(`${lang} catalog has no string at ${key}`)
  return value.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match))
}

async function eachVariant(page: Page, testInfo: TestInfo, name: string, check: (lang: Lang) => Promise<void>) {
  for (const [lang, theme] of VARIANTS) {
    await page.evaluate(([l, th]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', th) }, [lang, theme] as const)
    await page.reload()
    await check(lang)
    await testInfo.attach(`${name}-${lang}-${theme}`, { body: await page.screenshot({ animations: 'disabled' }), contentType: 'image/png' })
    await page.keyboard.press('Escape')
  }
}

async function register(page: Page, prefix: string) {
  const email = `${prefix}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  return email
}

test('an empty catalog explains datasets and a missing dataset links back', async ({ page }, testInfo) => {
  await page.goto('/login')
  await signIn(page, await register(page, 'emptyds'), 'secret12')
  await page.goto('/datasets')
  await eachVariant(page, testInfo, 'dataset-empty', async lang => {
    const empty = page.getByTestId('dataset-empty')
    await expect(empty.getByText(tx(lang, 'dataset.emptyTitle'))).toBeVisible()
    await expect(empty.getByText(tx(lang, 'dataset.emptyDescription'))).toBeVisible()
    await expect(empty.getByRole('button', { name: tx(lang, 'dataset.createDataset') })).toBeEnabled()
    await expect(empty.getByRole('link', { name: new RegExp(tx(lang, 'dataset.learnMore')) })).toHaveAttribute('href', /guide\/datasets/)
    await expect(page.getByText(tx(lang, 'dataset.selectDataset'), { exact: true })).toHaveCount(0)
    const box = (await empty.boundingBox())!
    expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width)
  })
  await page.getByTestId('dataset-empty').getByRole('button', { name: tx('vi', 'dataset.importCsv') }).click()
  await expect(page.getByRole('dialog', { name: tx('vi', 'dataset.createFromCsv') })).toBeVisible()
  await page.keyboard.press('Escape')

  await page.goto('/datasets/no-such-dataset')
  await eachVariant(page, testInfo, 'dataset-not-found', async lang => {
    const missing = page.getByTestId('dataset-not-found')
    await expect(missing.getByText(tx(lang, 'dataset.notFoundTitle'))).toBeVisible()
    await expect(missing.getByText(tx(lang, 'dataset.notFoundDescription'))).toBeVisible()
    await expect(page.getByRole('button', { name: tx(lang, 'common.retry') })).toHaveCount(0)
  })
  await page.getByTestId('dataset-not-found').getByRole('link', { name: tx('vi', 'dataset.backToDatasets') }).click()
  await expect(page).toHaveURL(/\/datasets$/)
  await expect(page.getByTestId('dataset-empty')).toBeVisible()
})

test('a viewer sees every dataset action disabled with the reason', async ({ page, browser }, testInfo) => {
  await page.goto('/login')
  const viewerEmail = await register(page, 'dsviewer')
  const viewerId = (await (await page.request.post('/api/auth/login', { data: { email: viewerEmail, password: 'secret12' } })).json()).data.user.id
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const teamId = (await (await page.request.post('/api/teams', { headers, data: { name: `Viewers ${Date.now().toString(36)}` } })).json()).data.id
  for (const email of ['admin@example.com', viewerEmail]) {
    expect((await page.request.post(`/api/teams/${teamId}/members`, { headers, data: { email } })).ok()).toBeTruthy()
  }
  expect((await page.request.patch(`/api/admin/users/${viewerId}`, { headers, data: { role: 'viewer' } })).ok()).toBeTruthy()
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: 'Viewer tickets', team_id: teamId, columns: [{ key: 'ticket', label: 'Ticket', kind: 'text', unique: true }],
  } })
  expect(created.ok()).toBeTruthy()
  const datasetId = (await created.json()).data.id
  expect((await page.request.post(`/api/datasets/${datasetId}/rows`, { headers, data: { values: { ticket: 'V-1' } } })).ok()).toBeTruthy()

  const context = await browser.newContext()
  const viewer = await context.newPage()
  await viewer.goto('/login')
  await signIn(viewer, viewerEmail, 'secret12')
  await viewer.goto(`/datasets/${datasetId}`)
  await eachVariant(viewer, testInfo, 'dataset-viewer', async lang => {
    const reason = tx(lang, 'dataset.viewOnlyReason')
    await expect(viewer.locator('#dataset-view-only')).toHaveText(reason)
    await expect(viewer.getByRole('button', { name: tx(lang, 'dataset.createDataset') })).toBeDisabled()
    await expect(viewer.getByRole('button', { name: tx(lang, 'dataset.addRow') })).toBeDisabled()
    await expect(viewer.getByRole('button', { name: tx(lang, 'dataset.addRow') })).toHaveAccessibleDescription(reason)
    await viewer.getByRole('button', { name: tx(lang, 'dataset.datasetActions') }).click()
    for (const key of ['dataset.editDataset', 'dataset.access', 'dataset.importCsv', 'dataset.deleteDataset']) {
      await expect(viewer.getByRole('menuitem', { name: tx(lang, key) })).toBeDisabled()
    }
    await expect(viewer.getByRole('menuitem', { name: tx(lang, 'dataset.exportCsv') })).toBeEnabled()
    await expect(viewer.getByRole('menu').getByText(reason)).toBeVisible()
  })
  await viewer.reload()
  await viewer.getByRole('button', { name: tx('vi', 'dataset.datasetActions') }).click()
  await viewer.getByRole('menuitem', { name: tx('vi', 'dataset.viewSchema') }).click()
  const schema = viewer.getByRole('tabpanel', { name: tx('vi', 'dataset.schema'), exact: true })
  await expect(schema.getByRole('button', { name: tx('vi', 'dataset.addColumn') })).toBeDisabled()
  await expect(schema.getByRole('button', { name: tx('vi', 'dataset.editColumnNamed', { name: 'Ticket' }) })).toBeDisabled()
  await expect(schema.getByText(tx('vi', 'dataset.viewOnlyReason'))).toBeVisible()
  await testInfo.attach('dataset-viewer-schema-vi', { body: await viewer.screenshot({ animations: 'disabled' }), contentType: 'image/png' })
  await context.close()
})

test('row deletion names the row and CSV issues list lines, columns and values', async ({ page }, testInfo) => {
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const created = await page.request.post('/api/datasets', { headers, data: {
    name: `Studio states ${Date.now().toString(36)}`,
    columns: [{ key: 'ticket', label: 'Ticket', kind: 'text', unique: true }, { key: 'score', label: 'Score', kind: 'number' }],
  } })
  expect(created.ok()).toBeTruthy()
  const datasetId = (await created.json()).data.id
  const rowsUrl = `/api/datasets/${datasetId}/rows`
  expect((await page.request.post(rowsUrl, { headers, data: { values: { ticket: 'T-1', score: 1 } } })).ok()).toBeTruthy()
  const unnamed = (await (await page.request.post(rowsUrl, { headers, data: { values: { score: 2 } } })).json()).data.row
  await page.goto(`/datasets/${datasetId}`)

  const rows = page.getByTestId('dataset-row')
  await eachVariant(page, testInfo, 'dataset-delete-row', async lang => {
    await expect(rows).toHaveCount(2)
    const named = rows.filter({ hasText: 'T-1' })
    await named.getByRole('button', { name: new RegExp(tx(lang, 'dataset.rowActions', { row: '\\d+' })) }).click()
    await page.getByRole('menuitem', { name: tx(lang, 'dataset.deleteRow') }).click()
    await expect(page.getByRole('alertdialog')).toContainText(tx(lang, 'dataset.deleteRowNamed', { field: 'Ticket', value: 'T-1' }))
  })
  await rows.filter({ hasNotText: 'T-1' }).getByRole('button', { name: new RegExp(tx('vi', 'dataset.rowActions', { row: '\\d+' })) }).click()
  await page.getByRole('menuitem', { name: tx('vi', 'dataset.deleteRow') }).click()
  await expect(page.getByRole('alertdialog')).toContainText(tx('vi', 'dataset.deleteRowById', { id: unnamed.id }))
  await page.keyboard.press('Escape')

  const long = 'x'.repeat(90)
  const csv = `Ticket,Score\nT-1,5\nT-2,not a number\nT-3\nT-4,${long}\n`
  await eachVariant(page, testInfo, 'dataset-csv-issues', async lang => {
    await page.getByRole('button', { name: tx(lang, 'dataset.datasetActions') }).click()
    await page.getByRole('menuitem', { name: tx(lang, 'dataset.importCsv') }).click()
    const importer = page.getByRole('dialog', { name: tx(lang, 'dataset.importCsv') })
    await importer.getByLabel(tx(lang, 'dataset.csvFile')).setInputFiles({ name: 'issues.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
    const issues = importer.getByTestId('dataset-csv-issues')
    await expect(issues).toContainText(tx(lang, 'dataset.csvIssuesTitle', { count: 4 }))
    await expect(issues).toContainText(tx(lang, 'dataset.csvIssueCount', { kind: tx(lang, 'dataset.csvIssueKind.DATASET_VALUE_INVALID'), count: 2 }))
    const lines = issues.locator('li')
    await expect(lines).toHaveCount(4)
    expect(await lines.evaluateAll(items => items.map(item => Number(item.getAttribute('data-csv-line'))))).toEqual([2, 3, 4, 5])
    await expect(lines.nth(0)).toContainText(`Ticket · ${tx(lang, 'dataset.csvRejectedValue', { value: 'T-1' })}`)
    await expect(lines.nth(1)).toContainText(`Score · ${tx(lang, 'dataset.csvRejectedValue', { value: 'not a number' })}`)
    await expect(lines.nth(3)).toContainText(`${'x'.repeat(59)}…`)
    await expect(lines.nth(3)).not.toContainText(long)
    await expect(importer.getByRole('columnheader').filter({ hasText: tx(lang, 'dataset.csvMappedTo', { label: 'Score' }) })).toBeVisible()
  })
})
