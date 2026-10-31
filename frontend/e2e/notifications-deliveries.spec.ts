import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import http from 'node:http'
import type { AddressInfo } from 'node:net'
// TASK-0020: notification bell for waiting runs; webhook delivery log with backoff, redelivery; signing-secret rotation.
const APPROVAL = {
  name: `Notify e2e ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 260, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve {{state.message}}?', output_field: 'decision' } },
    { id: 'e', type: 'end', position: { x: 500, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'e' }],
}
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}

test('notification bell: waiting run appears, opens the run, marks read', async ({ page }) => {
  const H = await login(page)
  await page.request.post('/api/notifications/read-all', { headers: H })
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: APPROVAL })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"message": "refund 42"}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  await page.goto('/workflows')
  await expect(page.locator('[data-testid=notify-count]')).toHaveText('1')
  await page.locator('#notify-bell').click()
  const item = page.locator('[data-testid=notify-item]').first()
  await expect(item).toContainText(APPROVAL.name); await expect(item).toContainText('Approve refund 42?'); await expect(item).toHaveAttribute('data-read', 'false')
  await item.click()
  await expect(page).toHaveURL(new RegExp(`/workflows/${wid}\\?run=`)); await expect(page.locator('#human-panel')).toBeVisible()
  await expect(page.locator('[data-testid=notify-count]')).toHaveCount(0)
  await page.locator('#notify-bell').click()
  await expect(page.locator('[data-testid=notify-item]').first()).toHaveAttribute('data-read', 'true')
  await page.keyboard.press('Escape'); await page.locator('#human-approve').click()
})

test('webhook deliveries: retried with backoff, logged, redelivered; secret rotation', async ({ page }) => {
  const codes = [500, 200]; const hits: string[] = []
  const srv = http.createServer((req, res) => { hits.push(String(req.headers['x-studio-signature'])); res.statusCode = codes.shift() ?? 200; res.end() })
  await new Promise<void>(r => srv.listen(0, '127.0.0.1', r)); const port = (srv.address() as AddressInfo).port
  try {
    const H = await login(page)
    await page.goto('/workflows/example'); await page.locator('#more-btn').click(); await page.locator('#api-btn').click()
    await page.locator('#api-token-name').fill('deliveries'); await page.locator('#api-create').click()
    const token = await page.locator('#api-token-value').inputValue(); const first = await page.locator('#api-signing-secret').inputValue()
    await page.request.post('/api/hooks/workflows/example/runs', { headers: { Authorization: `Bearer ${token}` }, data: { input: { message: 'hi' }, callback_url: `http://127.0.0.1:${port}/cb` } })
    await page.locator('#api-deliveries-tab').click()
    const row = page.locator('[data-testid=delivery-row]', { hasText: `127.0.0.1:${port}` }).first()
    // read without waiting: textContent() on a row that is not listed yet waits for it, so the poll would never click
    // Refresh again and the list would stay as it was before the delivery was logged (TASK-0209)
    const now = async (l: typeof row) => { await page.locator('#deliveries-refresh').click(); return (await l.allTextContents())[0] ?? '' }
    await expect.poll(() => now(row.locator('[data-testid=delivery-status]')), { timeout: 20_000 }).toBe('đã gửi')
    await expect(row).toContainText('2 lần thử'); await expect(row.locator('[data-testid=delivery-code]')).toHaveText('HTTP 200')
    await row.locator('[data-testid=delivery-redeliver]').click()
    await expect.poll(() => now(row), { timeout: 20_000 }).toContain('1 lần thử')
    expect(hits.length).toBe(3)
    // rotate the signing secret: shown once, the old one stays valid during the grace period
    await page.getByRole('tab', { name: 'Token' }).click()
    await page.locator('[data-testid=api-token-row]', { hasText: 'deliveries' }).first().locator('[data-testid=api-rotate]').click()
    await expect(page.locator('#api-rotated')).toBeVisible()
    const rotated = await page.locator('#api-signing-secret').inputValue()
    expect(rotated).toMatch(/^whsec_/); expect(rotated).not.toBe(first)
    void H
  } finally { srv.close() }
})

test('live push: a run waiting via the API rings the bell without polling; notification settings', async ({ page }) => {
  const H = await login(page)
  await page.request.post('/api/notifications/read-all', { headers: H })
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: { ...APPROVAL, name: `Live ${Date.now()}` } })).json()).data.id
  const tok = (await (await page.request.post(`/api/workflows/${wid}/tokens`, { headers: H, data: { name: 'live' } })).json()).data.token
  await page.goto('/workflows')
  await expect(page.locator('#notify-bell')).toHaveAttribute('data-live', 'true')
  await expect(page.locator('[data-testid=notify-count]')).toHaveCount(0)
  await page.request.post(`/api/hooks/workflows/${wid}/runs`, { headers: { Authorization: `Bearer ${tok}` }, data: { input: { message: 'live 1' } } })
  await expect(page.locator('[data-testid=notify-count]')).toHaveText('1', { timeout: 8_000 })  // well under the 30 s poll
  await page.locator('#notify-bell').click(); await page.locator('#notify-settings').click()
  const dlg = page.locator('#notify-settings-dialog'); await expect(dlg).toBeVisible()
  await expect(page.locator('#notify-email-off')).toBeVisible()  // no SMTP in e2e
  const email = page.locator('#notify-pref-email'); await expect(email).toHaveAttribute('data-state', 'checked')
  await email.click(); await expect(email).toHaveAttribute('data-state', 'unchecked')
  const prefs = (await (await page.request.get('/api/notifications/preferences', { headers: H })).json()).data
  expect(prefs).toMatchObject({ in_app: true, email: false })
  await email.click(); await expect(email).toHaveAttribute('data-state', 'checked')
})
