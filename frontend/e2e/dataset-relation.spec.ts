import { expect, test, type Page, type TestInfo } from '@playwright/test'
import type { Dataset, DatasetRow, DatasetRowResult } from '../src/lib/datasets'
import { signIn } from './helpers'
import { vt } from './catalog'

async function send<T>(page: Page, headers: Record<string, string>, method: string, path: string, data?: unknown): Promise<T> {
  const response = await page.request.fetch(path, { headers, method, data })
  expect(response.ok(), await response.text()).toBeTruthy()
  return (await response.json()).data
}

async function capture(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(`${name}.png`)
  await page.screenshot({ path, animations: 'disabled' })
  await testInfo.attach(name, { path, contentType: 'image/png' })
}

const textColumn = (key: string, label: string) => ({ key, label, kind: 'text' })
const datasetPath = (id: string) => `/api/datasets/${id}`
const relationColumn = (target: Dataset) => ({
  key: 'company', label: 'Company', kind: 'relation',
  relation: { target_dataset_id: target.id, display_key: 'name' },
})
const companyCell = (page: Page) => page.getByRole('button', { name: /^Edit Company:/ }).first()
const picker = (page: Page) => page.getByRole('dialog', { name: 'Choose a linked record' })
const companySearch = (page: Page) => picker(page).getByRole('combobox', { name: 'Search linked records' })

async function session(page: Page) {
  await page.addInitScript(() => {
    const lang = new URLSearchParams(location.search).get('testLocale') === 'vi' ? 'vi' : 'en'
    localStorage.setItem('lang', lang)
  })
  await page.goto('/login')
  return { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
}

test('Relation schema chooses an eligible target and keeps it fixed', async ({ page }, testInfo) => {
  const headers = await session(page)
  const team = await send<{ id: string }>(page, headers, 'POST', '/api/teams', { name: 'Relation schema team' })
  await send(page, headers, 'POST', `/api/teams/${team.id}/members`, { email: 'admin@example.com' })
  const target = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Schema companies', team_id: team.id,
    columns: [textColumn('name', 'Name'), { key: 'rating', label: 'Rating', kind: 'number' }, textColumn('alias', 'Alias')],
  })
  const numeric = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Schema numeric only', team_id: team.id, columns: [{ key: 'rating', label: 'Rating', kind: 'number' }],
  })
  await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Personal schema companies', columns: [textColumn('name', 'Name')],
  })
  const source = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Schema tickets', team_id: team.id, columns: [textColumn('subject', 'Subject')],
  })

  await page.goto(`/datasets/${source.id}?tab=schema&theme=light`)
  await page.getByRole('button', { name: 'Add column' }).click()
  const form = page.getByRole('dialog', { name: 'Add column' })
  await form.getByRole('textbox', { name: 'Column label' }).fill('Company')
  await form.getByRole('textbox', { name: 'Field key' }).fill('company')
  const type = form.getByRole('combobox', { name: 'Column type' })
  await type.click()
  await page.getByRole('option', { name: 'Relation', exact: true }).click()
  const targetSelect = form.getByRole('combobox', { name: 'Target dataset' })
  await expect(targetSelect).toBeEnabled()
  const typeBox = (await type.boundingBox())!
  const targetBox = (await targetSelect.boundingBox())!
  expect(typeBox.y).toBeCloseTo(targetBox.y, 0)
  expect(typeBox.width).toBeCloseTo(targetBox.width, 0)
  await targetSelect.click()
  await expect(page.getByRole('option', { name: 'Personal schema companies' })).toHaveCount(0)
  await expect(page.getByRole('option', { name: source.name })).toHaveCount(0)
  await page.getByRole('option', { name: numeric.name }).click()
  const display = form.getByRole('combobox', { name: 'Display column' })
  await expect(display).toBeEnabled()
  await display.click()
  await expect(page.getByText('No eligible text columns')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(form.getByRole('button', { name: 'Save', exact: true })).toBeDisabled()

  await targetSelect.click()
  await page.getByRole('option', { name: target.name }).click()
  await display.click()
  await expect(page.getByRole('option', { name: 'Rating' })).toHaveCount(0)
  await page.getByRole('option', { name: 'Name', exact: true }).click()
  await capture(page, testInfo, 'relation-schema-light')
  await form.getByRole('button', { name: 'Save', exact: true }).click()
  const schema = page.getByRole('tabpanel', { name: 'Schema' })
  await expect(schema.getByRole('link', { name: target.name })).toBeVisible()
  await schema.getByRole('button', { name: 'Edit Company' }).click()
  const edit = page.getByRole('dialog', { name: 'Edit column' })
  await expect(edit.getByRole('combobox', { name: 'Target dataset' })).toBeDisabled()
  await edit.getByRole('combobox', { name: 'Display column' }).click()
  await page.getByRole('option', { name: 'Alias' }).click()
  await edit.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(edit).toBeHidden()
  const definition = await send<Dataset>(page, headers, 'GET', datasetPath(source.id))
  expect(definition.columns.find(column => column.key === 'company')?.relation).toEqual({
    target_dataset_id: target.id, display_key: 'alias',
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/datasets/${source.id}?tab=schema&theme=dark&testLocale=vi`)
  await page.getByRole('button', { name: vt('dataset.editColumnNamed', { name: 'Company' }) }).click()
  const mobile = page.getByRole('dialog', { name: vt('dataset.editColumn') })
  const mobileType = (await mobile.getByRole('combobox', { name: vt('dataset.columnType') }).boundingBox())!
  const mobileTarget = (await mobile.getByRole('combobox', { name: vt('dataset.relation.target') }).boundingBox())!
  expect(mobileTarget.y).toBeGreaterThan(mobileType.y)
  await capture(page, testInfo, 'relation-schema-mobile-dark')
})

test('Relation picker pages, searches, filters, guards deletions and confirms unlink', async ({ page }, testInfo) => {
  const headers = await session(page)
  const target = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Picker companies', columns: [textColumn('name', 'Name')],
  })
  const source = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
    name: 'Picker tickets', columns: [textColumn('subject', 'Subject'), relationColumn(target)],
  })
  const companiesPath = `${datasetPath(target.id)}/rows`
  const ticketsPath = `${datasetPath(source.id)}/rows`
  const linked = (await send<DatasetRowResult>(page, headers, 'POST', companiesPath, { values: { name: 'Northwind' } })).row
  const duplicate = (await send<DatasetRowResult>(page, headers, 'POST', companiesPath, { values: { name: 'Northwind' } })).row
  await send(page, headers, 'POST', '/api/datasets/csv/import', {
    dataset_id: target.id, schema_revision: target.revision,
    text: 'Name\n' + Array.from({ length: 26 }, (_, index) => `Company ${String(index).padStart(2, '0')}\n`).join(''),
  })
  const ticket = (await send<DatasetRowResult>(page, headers, 'POST', ticketsPath, { values: { subject: 'Printer setup' } })).row
  await send<DatasetRowResult>(page, headers, 'POST', ticketsPath, { values: { subject: 'Open ticket' } })
  await page.goto(`/datasets/${source.id}?theme=dark`)

  await companyCell(page).click()
  await expect(page.getByRole('button', { name: 'Choose a linked record' })).toBeVisible()
  await companyCell(page).press('Enter')
  await expect(companySearch(page)).toBeFocused()
  await picker(page).getByRole('button', { name: 'Next page' }).click()
  await expect(picker(page).getByRole('option').filter({ hasText: duplicate.id })).toBeVisible()
  await picker(page).getByRole('button', { name: 'Previous page' }).click()
  await expect(picker(page).getByRole('option').filter({ hasText: 'Company 00' })).toBeVisible()
  await companySearch(page).fill('does not exist')
  await expect(picker(page).getByText('No matching records')).toBeVisible()
  await companySearch(page).fill('Northwind')
  await expect(picker(page).getByRole('option').filter({ hasText: linked.id })).toBeVisible()
  await expect(picker(page).getByRole('option').filter({ hasText: duplicate.id })).toBeVisible()
  await capture(page, testInfo, 'relation-picker-dark')
  await page.keyboard.press('Escape')
  await expect(companyCell(page)).toBeFocused()
  await page.getByRole('button', { name: 'Choose a linked record' }).click()
  await companySearch(page).fill('Northwind')
  const chosen = picker(page).getByRole('option').filter({ hasText: linked.id })
  await expect(chosen).toBeVisible()
  await chosen.hover()
  await companySearch(page).press('Enter')
  await expect(companyCell(page)).toHaveAccessibleName('Edit Company: Northwind')
  await expect(companyCell(page)).toBeFocused()

  await page.getByRole('button', { name: 'Filter', exact: true }).click()
  await page.getByRole('combobox', { name: 'Filter column' }).click()
  await page.getByRole('option', { name: 'Company', exact: true }).click()
  await page.getByRole('button', { name: 'Filter value' }).click()
  await companySearch(page).fill('Northwind')
  await picker(page).getByRole('option').filter({ hasText: linked.id }).click()
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByText('Open ticket', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Printer setup', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Filter', exact: true }).click()
  await page.getByRole('combobox', { name: 'Filter operator' }).click()
  await page.getByRole('option', { name: 'Is empty', exact: true }).click()
  await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByText('Printer setup', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Open ticket', { exact: true })).toBeVisible()

  await page.goto(`/datasets/${target.id}?theme=dark`)
  await page.getByRole('button', { name: 'Row 1 actions', exact: true }).click()
  await page.getByRole('menuitem', { name: 'Delete row' }).click()
  const removal = page.getByRole('alertdialog', { name: 'Delete row' })
  await removal.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(removal.getByRole('alert')).toContainText('Remove the referencing relations')
  await removal.getByRole('button', { name: 'Cancel' }).click()
  await expect(page.getByRole('button', { name: 'Edit Name: Northwind', exact: true }).first()).toBeVisible()
  await send<DatasetRowResult>(page, headers, 'PATCH', `${companiesPath}/${linked.id}`, { revision: linked.revision, values: { name: 'Northwind renamed' } })

  await page.goto(`/datasets/${source.id}?theme=dark`)
  await expect(companyCell(page)).toHaveAccessibleName('Edit Company: Northwind renamed')
  await companyCell(page).dblclick()
  await picker(page).getByRole('button', { name: 'Unlink record' }).click()
  const confirmation = page.getByRole('alertdialog', { name: 'Unlink record' })
  const unlink = confirmation.getByRole('button', { name: 'Unlink record' })
  await expect(unlink).toBeDisabled()
  await confirmation.getByPlaceholder('Type the name exactly').fill('Northwind renamed')
  await unlink.click()
  await expect(confirmation).toBeHidden()
  await expect(companyCell(page)).toBeFocused()
  const saved = await send<DatasetRow>(page, headers, 'GET', `${ticketsPath}/${ticket.id}`)
  expect(saved.values.company).toBeNull()
})

test('Relation labels are visible to a viewer while stale or unavailable links are handled', async ({ page, browser }) => {
  const headers = await session(page)
  const team = await send<{ id: string }>(page, headers, 'POST', '/api/teams', { name: 'Relation viewer team' })
  const context = await browser.newContext()
  try {
    const viewer = await context.newPage()
    await viewer.addInitScript(() => localStorage.setItem('lang', 'en'))
    await viewer.goto('/login')
    const email = 'relation-viewer@example.com'
    const registered = await send<{ user: { id: string } }>(viewer, {}, 'POST', '/api/auth/register', { email, password: 'secret12' })
    for (const member of ['admin@example.com', email]) {
      await send(page, headers, 'POST', `/api/teams/${team.id}/members`, { email: member })
    }
    await send(page, headers, 'PATCH', `/api/admin/users/${registered.user.id}`, { role: 'viewer' })
    const target = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
      name: 'Viewer companies', team_id: team.id, columns: [textColumn('name', 'Name')],
    })
    const source = await send<Dataset>(page, headers, 'POST', '/api/datasets', {
      name: 'Viewer relation tickets', team_id: team.id, columns: [textColumn('subject', 'Subject'), relationColumn(target)],
    })
    const targetPath = datasetPath(target.id)
    const sourcePath = datasetPath(source.id)
    const company = (await send<DatasetRowResult>(page, headers, 'POST', `${targetPath}/rows`, { values: { name: 'Visible company' } })).row
    const another = (await send<DatasetRowResult>(page, headers, 'POST', `${targetPath}/rows`, { values: { name: 'Another company' } })).row
    const row = (await send<DatasetRowResult>(page, headers, 'POST', `${sourcePath}/rows`, { values: { subject: 'Visible ticket' } })).row
    const link = await send<{ revision: number }>(page, headers, 'PUT', `${sourcePath}/rows/${row.id}/relations/company`, {
      target_row_id: company.id, revision: row.revision, schema_revision: source.revision,
    })
    await signIn(viewer, email, 'secret12')
    await viewer.goto(`/datasets/${source.id}`)
    const readOnly = viewer.getByRole('button', { name: 'Company: Visible company', exact: true })
    await expect(readOnly).toBeVisible()
    await readOnly.dblclick()
    await expect(picker(viewer)).toHaveCount(0)
    await expect(viewer.getByRole('button', { name: 'Add row' })).toBeDisabled()
    await viewer.route('**/columns/company/relation/rows?**', route => route.fulfill({
      status: 404, json: { success: false, data: null, error: { code: 'DATASET_RELATION_TARGET_INVALID' } },
    }))
    await viewer.reload()
    await expect(viewer.getByRole('button', { name: 'Company: Link unavailable', exact: true })).toBeVisible()
    await expect(viewer.getByText(company.id)).toHaveCount(0)

    await page.goto(`/datasets/${source.id}`)
    await companyCell(page).dblclick()
    await companySearch(page).fill('Another company')
    const choice = picker(page).getByRole('option').filter({ hasText: another.id })
    await expect(choice).toBeVisible()
    await send<DatasetRowResult>(page, headers, 'PATCH', `${sourcePath}/rows/${row.id}`, { revision: link.revision, values: { subject: 'Updated elsewhere' } })
    await choice.click()
    await expect(picker(page).getByRole('alert')).toContainText('The row changed')
    await expect(companyCell(page)).toHaveAccessibleName('Edit Company: Visible company')
    const saved = await send<DatasetRow>(page, headers, 'GET', `${sourcePath}/rows/${row.id}`)
    expect(saved.values.company).toBe(company.id)
  } finally {
    await context.close()
  }
})
