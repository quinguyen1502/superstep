import { expect, test, type Browser, type Page, type WebSocketRoute } from '@playwright/test'
import { signIn } from './helpers'

const columns = [
  { key: 'ticket', label: 'Ticket', kind: 'text', unique: true },
  { key: 'team', label: 'Team', kind: 'select', options: ['Support', 'Billing'] },
  { key: 'score', label: 'Score', kind: 'number' },
]

async function owner(page: Page) {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  return { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
}

async function sharedGrid(page: Page, browser: Browser, name: string) {
  const headers = await owner(page)
  const context = await browser.newContext()
  const viewer = await context.newPage()
  const stamp = Date.now().toString(36)
  const email = `live-${stamp}@example.com`
  const registration = await viewer.request.post('/api/auth/register', { data: { email, password: 'secret12' } })
  expect(registration.ok()).toBeTruthy()
  const { user } = (await registration.json()).data
  const team = (await (await page.request.post('/api/teams', { headers, data: { name: `${name} ${stamp}` } })).json()).data
  for (const member of ['admin@example.com', email]) {
    expect((await page.request.post(`/api/teams/${team.id}/members`, { headers, data: { email: member } })).ok()).toBeTruthy()
  }
  const created = await page.request.post('/api/datasets', { headers, data: { name, team_id: team.id, columns } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const path = `/datasets/${dataset.id}`
  const rows = `/api${path}/rows`
  const inserted = await page.request.post(rows, {
    headers, data: { values: { ticket: 'Printer jam', team: 'Support', score: 1 }, schema_revision: dataset.revision },
  })
  expect(inserted.ok()).toBeTruthy()
  await viewer.addInitScript(() => localStorage.setItem('lang', 'en'))
  await viewer.goto('/login')
  await signIn(viewer, email, 'secret12')
  return { context, viewer, path, rows, headers, dataset, teamId: team.id as string, userId: user.id as string }
}

test('refreshes an open group and summary while keeping edits and their row conflicts', async ({ page, browser }) => {
  const fixture = await sharedGrid(page, browser, 'Live shared totals')
  const { context, viewer, path, headers, dataset } = fixture
  let pushedRevision = 0
  viewer.on('websocket', stream => {
    if (new URL(stream.url()).pathname !== `/ws${path}/changes`) return
    stream.on('framereceived', ({ payload }) => {
      const marker = JSON.parse(String(payload))
      if (marker.type === 'dataset_changed') pushedRevision = marker.data_revision
    })
  })
  try {
    await viewer.goto(path)
    const query = viewer.getByRole('searchbox', { name: 'Search rows' })
    await query.fill('Printer')
    await viewer.getByRole('combobox', { name: 'Group by' }).click()
    await viewer.getByRole('option', { name: 'Team', exact: true }).click()
    await viewer.getByRole('button', { name: 'Summary', exact: true }).click()
    const summary = viewer.getByRole('combobox', { name: 'Summary for Score' })
    await summary.click()
    await viewer.getByRole('option', { name: 'Sum', exact: true }).click()
    const group = viewer.getByRole('button', { name: /^Support \d+ rows?$/ })
    await expect(group).toHaveText('Support1 row')
    await group.click()
    const initialCell = viewer.getByRole('button', { name: /^Edit Score: 1$/ })
    await expect(initialCell).toBeVisible()
    await initialCell.focus()

    await page.goto(path)
    await page.getByRole('button', { name: /^Edit Score: 1$/ }).press('Enter')
    const writer = page.getByRole('spinbutton', { name: 'Score' })
    await writer.fill('4')
    await writer.press('Enter')
    await expect(viewer.getByRole('button', { name: /^Edit Score: 4$/ })).toBeFocused()
    await expect(summary).toContainText('Sum: 4')
    await expect(viewer.getByText('Score · Sum 4')).toBeVisible()

    const cell = viewer.getByRole('button', { name: /^Edit Score: 4$/ })
    await cell.press('Enter')
    const editor = viewer.getByRole('spinbutton', { name: 'Score' })
    await editor.fill('99')
    let groupQueries = 0
    viewer.on('request', request => {
      if (new URL(request.url()).pathname === `/api${path}/rows/groups/query`) groupQueries++
    })
    await page.getByRole('button', { name: /^Edit Score: 4$/ }).press('Enter')
    await writer.fill('7')
    await writer.press('Enter')
    await expect(page.getByRole('button', { name: /^Edit Score: 7$/ })).toBeVisible()

    const imported = await page.request.post('/api/datasets/csv/import', { headers, data: {
      dataset_id: dataset.id, schema_revision: dataset.revision, mapping: ['ticket', 'team', 'score'],
      text: 'Ticket,Team,Score\nPrinter cable,Support,2\nPrinter parts,Support,3\nClosed order,Billing,100\n',
    } })
    expect(imported.ok()).toBeTruthy()
    await expect(editor).toBeFocused()
    await expect(editor).toHaveValue('99')
    await expect(summary).toContainText('Sum: 4')
    const revisions = await page.request.get(`/api${path}/revisions`, { headers })
    expect(revisions.ok()).toBeTruthy()
    const { data_revision: committedRevision } = (await revisions.json()).data
    await expect.poll(() => pushedRevision).toBe(committedRevision)
    // Give the last received frame a full debounce window while the draft is still open.
    await viewer.evaluate(() => new Promise<void>(resolve => setTimeout(resolve, 250)))
    expect(groupQueries).toBe(0)
    await editor.press('Enter')
    await expect(viewer.getByText('The row changed. Reload it and try again')).toBeVisible()
    await expect(editor).toHaveValue('99')
    await editor.press('Escape')
    await expect(group).toHaveText('Support3 rows')
    await expect(group).toHaveAttribute('aria-expanded', 'true')
    await expect(summary).toContainText('Sum: 12')
    await expect(viewer.getByText('Score · Sum 12')).toBeVisible()
    await expect(viewer.getByTestId('dataset-row')).toHaveCount(3)
    await expect(query).toHaveValue('Printer')
    expect(groupQueries).toBe(1)
  } finally {
    await context.close()
  }
})

test('resyncs on focus and reconnect without resetting the sorted viewport', async ({ page }, info) => {
  const headers = await owner(page)
  const created = await page.request.post('/api/datasets', { headers, data: { name: 'Live viewport', columns } })
  expect(created.ok()).toBeTruthy()
  const dataset = (await created.json()).data
  const path = `/datasets/${dataset.id}`
  const rows = `/api${path}/rows`
  const imported = await page.request.post('/api/datasets/csv/import', { headers, data: {
    dataset_id: dataset.id, schema_revision: dataset.revision, mapping: ['ticket', 'team', 'score'],
    text: 'Ticket,Team,Score\n' + Array.from({ length: 75 }, (_, i) => `T-${String(i).padStart(3, '0')},Support,${i + 1}`).join('\n'),
  } })
  expect(imported.ok()).toBeTruthy()
  let stream: WebSocketRoute | undefined
  let dropChanges = false
  let blocked = false
  let dropRevisions = false
  await page.routeWebSocket(`**/ws${path}/changes`, route => {
    if (blocked) return route.close({ code: 1011 })
    stream = route
    const server = route.connectToServer()
    server.onMessage(message => {
      if (dropChanges && JSON.parse(String(message)).type === 'dataset_changed') return
      route.send(message)
    })
  })
  await page.route(`**/api${path}/revisions`, route => dropRevisions ? route.abort() : route.continue())
  await page.setViewportSize({ width: 620, height: 690 })
  await page.goto(path)
  const footer = page.getByTestId('dataset-grid-footer')
  await expect(footer).toContainText('1–50 of 75')
  await page.getByRole('button', { name: 'Ticket Unique' }).click()
  const header = page.getByRole('columnheader', { name: 'Ticket Unique' })
  await expect(header).toHaveAttribute('aria-sort', 'ascending')
  await expect(footer).toContainText('1–50 of 75')
  const viewport = page.getByRole('table', { name: 'Grid view' }).locator('..')
  await viewport.evaluate(node => { node.scrollTop = node.scrollHeight })
  await expect(footer).toContainText('1–75 of 75')
  const before = await viewport.evaluate(node => node.scrollTop)

  dropChanges = true
  const added = await page.request.post(rows, {
    headers, data: { values: { ticket: 'T-075', team: 'Support', score: 76 }, schema_revision: dataset.revision },
  })
  expect(added.ok()).toBeTruthy()
  const focusRead = page.waitForResponse(`**/api${path}/revisions`)
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  expect((await focusRead).ok()).toBeTruthy()
  await expect(footer).toContainText('1–76 of 76')
  expect(Math.abs((await viewport.evaluate(node => node.scrollTop)) - before)).toBeLessThan(41)
  await expect(header).toHaveAttribute('aria-sort', 'ascending')

  blocked = true
  const disconnectedRead = page.waitForResponse(`**/api${path}/revisions`)
  await stream!.close({ code: 1011 })
  await expect(footer).toContainText('Live updates are delayed.')
  for (const theme of ['light', 'dark']) {
    await page.evaluate(active => document.documentElement.classList.toggle('dark', active === 'dark'), theme)
    const screenshot = info.outputPath(`dataset-live-delayed-${theme}.png`)
    await page.screenshot({ path: screenshot, animations: 'disabled' })
    await info.attach(`dataset-live-delayed-${theme}`, { path: screenshot, contentType: 'image/png' })
  }
  expect((await disconnectedRead).ok()).toBeTruthy()
  expect((await page.request.post(rows, {
    headers, data: { values: { ticket: 'T-076', team: 'Support', score: 77 }, schema_revision: dataset.revision },
  })).ok()).toBeTruthy()
  await expect(footer).toContainText('1–77 of 77', { timeout: 12_000 })
  await expect(footer).toContainText('Live updates are delayed.')
  dropRevisions = true
  const definition = await page.request.post(`/api${path}/columns`, { headers, data: {
    revision: dataset.revision, column: { key: 'note', label: 'New note', kind: 'text' },
  } })
  expect(definition.ok()).toBeTruthy()
  dropChanges = false
  blocked = false
  await expect(page.getByRole('columnheader', { name: 'New note' })).toHaveCount(1)
  await expect(footer).not.toContainText('Live updates are delayed.')
  await expect(footer).toContainText('1–77 of 77')
  await expect(header).toHaveAttribute('aria-sort', 'ascending')
})

test('removes the grid and a pending draft when a team member loses access', async ({ page, browser }) => {
  const { context, viewer, path, rows, headers, dataset, teamId, userId } = await sharedGrid(page, browser, 'Live revoked viewer')
  try {
    await viewer.goto(path)
    await viewer.getByRole('button', { name: /^Edit Ticket: Printer jam$/ }).dblclick()
    const draft = viewer.getByRole('textbox', { name: 'Ticket' })
    await draft.fill('Private draft')
    expect((await page.request.delete(`/api/teams/${teamId}/members/${userId}`, { headers })).ok()).toBeTruthy()
    // A committed write wakes the real subscription and forces an immediate visibility check.
    expect((await page.request.post(rows, {
      headers, data: { values: { ticket: 'Private new row', team: 'Billing', score: 2 }, schema_revision: dataset.revision },
    })).ok()).toBeTruthy()
    await expect(viewer.getByText('You no longer have access to this dataset, or it was deleted.')).toBeVisible()
    await expect(viewer.getByRole('table', { name: 'Grid view' })).toHaveCount(0)
    await expect(viewer.getByText('Printer jam')).toHaveCount(0)
    await expect(draft).toHaveCount(0)
    await expect(viewer.getByRole('link', { name: 'Live revoked viewer' })).toHaveCount(0)
  } finally {
    await context.close()
  }
})
