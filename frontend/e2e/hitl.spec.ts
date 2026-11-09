import { test, expect, type Page } from '@playwright/test'
import { apiToken, signIn } from './helpers'
// a run pauses at a Human node, shows up as pending, and resumes from the panel.
const APPROVAL = {
  name: `Approval e2e ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 260, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve refund for {{state.message}}?', output_field: 'decision' } },
    { id: 'route', type: 'condition', position: { x: 500, y: 150 }, data: { label: 'Approved?', field: 'decision', default: 'rejected' } },
    { id: 'e', type: 'end', position: { x: 740, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'route' },
    { id: '3', source: 'route', target: 'e', label: 'approved' }, { id: '4', source: 'route', target: 'e', label: 'rejected' }],
}
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return apiToken(page)
}

test('human node: wait, pending list, approve, complete', async ({ page }) => {
  const token = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: APPROVAL })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#human-prompt')).toHaveText('Approve refund for message?'); await expect(page.locator('#human-prompt .template-tag[data-field="message"]')).toBeVisible()
  await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"message": "order A100"}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  await expect(page.locator('#human-question')).toHaveText('Approve refund for order A100?')
  // the workflows page and the header badge lead to the Approvals inbox, which links back to the run
  await page.goto('/workflows')
  await expect(page.locator('[data-testid=pending-count]')).toBeVisible()  // header badge
  expect(Number(await page.locator('[data-testid=pending-count]').textContent())).toBeGreaterThan(0)
  await page.locator('#pending-runs-open').click(); await expect(page).toHaveURL(/\/approvals$/)
  const row = page.locator('[data-testid=inbox-row]', { hasText: APPROVAL.name }); await expect(row).toBeVisible()
  await expect(row.locator('[data-testid=inbox-question]')).toHaveText('Approve refund for order A100?')
  await row.locator('[data-testid=inbox-open]').click()
  await expect(page).toHaveURL(new RegExp(`/workflows/${wid}\\?run=`))
  // Wait for the reopened run to hydrate (history fetch can lag under WebServer resets).
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  await expect(page.locator('#human-panel')).toBeVisible({ timeout: 30_000 })
  await page.locator('#human-approve').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(page.locator('#human-panel')).toHaveCount(0)
  await expect(page.locator('.trace-row[data-span="ask#1"]')).toHaveCount(1) // the resumed Human node keeps one span
  await page.goto('/approvals'); await expect(page.locator('[data-testid=inbox-row]', { hasText: APPROVAL.name })).toHaveCount(0)
})

test('approvals inbox: a listed approver answers in place', async ({ page, browser }) => {
  const token = await login(page); const email = `appr${Date.now()}@example.com`
  const other = await browser.newPage(); await other.request.post('/api/auth/register', { data: { email, password: 'secret12' } })  // its own session
  const wf = { ...APPROVAL, name: `Inbox e2e ${Date.now()}`, nodes: APPROVAL.nodes.map(n => n.id === 'ask' ? { ...n, data: { ...n.data, approval: { approvers: [email] } } } : n) }
  const wid = (await (await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: wf })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#approval-approvers')).toHaveValue(email)  // approvers on a studio-only Human node
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order B7"}')
  await page.locator('#run-btn').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })

  await other.goto('/login'); await signIn(other, email, 'secret12'); await other.goto('/approvals')
  const row = other.locator('[data-testid=inbox-row]', { hasText: wf.name }); await expect(row).toBeVisible()
  await expect(row.locator('[data-testid=inbox-owner]')).toContainText('admin@example.com')
  await expect(row.locator('[data-testid=inbox-open]')).toHaveCount(0)  // the run itself stays the owner's
  await row.locator('[data-testid=answer-reject]').click()
  await expect(other.locator('#inbox-sent')).toBeVisible(); await expect(row).toHaveCount(0)
  await other.close()
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: { Authorization: `Bearer ${token}` } })).json()).data[0].final_state?.decision,
    { timeout: 30_000 }).toBe('rejected')
})

test('human node deadline: settings, due time in the inbox, rejected on time', async ({ page }) => {
  test.setTimeout(150_000)
  const token = await login(page)
  const wf = { ...APPROVAL, name: `Deadline e2e ${Date.now()}` }
  const wid = (await (await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: wf })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click()
  await page.locator('#config-tab-settings').click()
  await page.locator('#deadline-on').click(); await expect(page.locator('#deadline-after')).toHaveValue('1')
  await page.locator('#deadline-action').click(); await page.getByRole('option', { name: 'Chuyển cho người duyệt khác' }).click()
  await expect(page.locator('#deadline-escalate')).toBeVisible()
  await page.locator('#deadline-action').click(); await page.getByRole('option', { name: 'Từ chối' }).click()
  await page.locator('#deadline-after-unit').click(); await page.getByRole('option', { name: 'phút' }).click()
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: { Authorization: `Bearer ${token}` } })).json()).data
  expect(saved.nodes.find((n: { id: string }) => n.id === 'ask').data.deadline).toEqual({ after: '1m', on_timeout: 'reject' })
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order C3"}')
  await page.locator('#run-btn').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  await page.goto('/approvals')
  await expect(page.locator('[data-testid=inbox-row]', { hasText: wf.name }).locator('[data-testid=inbox-due]')).toBeVisible()
  // one minute later the worker's sweep rejects it
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: { Authorization: `Bearer ${token}` } })).json()).data[0].final_state?.decision,
    { timeout: 100_000, intervals: [5_000] }).toBe('rejected')
  await page.reload(); await expect(page.locator('[data-testid=inbox-row]', { hasText: wf.name })).toHaveCount(0)
})
