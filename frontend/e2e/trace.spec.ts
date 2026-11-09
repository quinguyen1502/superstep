import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import { vt } from './catalog'

async function loginAdmin(page: Page) {
  await page.goto('/login'); await page.getByLabel(vt('auth.password'), { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
}
const LOOP = {
  name: 'Loop demo (recursion limit)', state: [{ name: 'message', type: 'string' }, { name: 'intent', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'think', type: 'llm', position: { x: 260, y: 150 }, data: { label: 'Think', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
    { id: 'check', type: 'condition', position: { x: 500, y: 150 }, data: { label: 'Check done?', field: 'intent', default: 'again' } },
    { id: 'e', type: 'end', position: { x: 740, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'think' }, { id: '2', source: 'think', target: 'check' },
    { id: '3', source: 'check', target: 'think', label: 'again' }, { id: '4', source: 'check', target: 'e', label: 'done' }],
}

test('trace timeline: rows, detail tabs, diff, canvas sync, raw toggle, history replay', async ({ page }) => {
  await loginAdmin(page); await page.goto('/workflows/example')
  await page.locator('#run-btn').click()
  const summary = page.locator('#trace-summary')
  await expect(summary).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(summary).toContainText('Hoàn thành')
  const rows = page.locator('.trace-row'); await expect(rows).toHaveCount(6) // start, classify, route, lookup, reply_order, end
  await page.locator('.trace-row[data-span="classify#1"]').click()
  await expect(page.locator('#trace-detail')).toContainText('Classify intent')
  await expect(page.locator('#trace-diff [data-kind="added"]')).toContainText('intent')
  await page.getByRole('tab', { name: 'Input' }).last().click()
  await expect(page.locator('#trace-detail')).toContainText('message')
  // canvas click selects matching row
  await page.locator('.react-flow__node[data-id="lookup"]').click()
  await expect(page.locator('.trace-row[data-span="lookup#1"]')).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('#trace-detail')).toContainText('Lookup order')
  // raw toggle
  await page.locator('#raw-toggle').check(); await expect(page.locator('#raw-events')).toContainText('node_finished')
  await page.locator('#raw-toggle').uncheck()
  // history replay uses same timeline
  await page.locator('#history-all').click()
  await page.getByTestId('history-row').first().click()
  await expect(summary).toContainText('Replay')
  await expect(rows.first()).toBeVisible()
})

test('trace timeline: loop iterations (#2, #3) and node error highlighted', async ({ page }) => {
  await loginAdmin(page)
  const token = await apiToken(page)
  const r = await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: LOOP })
  await page.goto(`/workflows/${(await r.json()).data.id}`)
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'error', { timeout: 30_000 })
  await expect(page.locator('.trace-row[data-span="think#3"]')).toContainText('#3')
  const err = page.locator('.trace-row.bg-destructive\\/5'); await expect(err).toHaveCount(1)
  await err.click(); await expect(page.locator('#trace-detail [role=alert]')).toContainText('Recursion')
})
