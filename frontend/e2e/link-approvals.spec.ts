import { test, expect } from '@playwright/test'
import { login } from './helpers'
import { vt } from './catalog'
// a Teams channel (the fake Workflows webhook of backend/tests/fixtures/mock_chat_api.py) gets a card whose
// buttons open /approve; the signed-in owner confirms there and the run goes on. E-mail uses the same page.
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
const hook = `${CHAT}/teams/hook-${Date.now()}`
const WF = (name: string, approval: object) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 260, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve refund for {{state.message}}?', output_field: 'decision', approval } },
    { id: 'e', type: 'end', position: { x: 500, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'e' }] })

test('Teams card → /approve → run resumes; the link works once', async ({ page }) => {
  const H = await login(page)
  const ch = (await (await page.request.post('/api/approvals/channels', { headers: H, data: { kind: 'teams', webhook_url: hook } })).json()).data
  await page.goto('/settings/channels')
  await expect(page.locator(`[data-channel-id="${ch.id}"]`)).toContainText(vt('approvals.linkNote'))  // no callback URL for a link channel

  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: WF(`Teams ${Date.now()}`, { channel_id: ch.id, channel: 'teams', target: '' }) })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click(); await expect(page.locator('#approval-no-target')).toBeVisible()
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order A100"}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })

  let card: any
  await expect.poll(async () => { card = (await (await page.request.get(`${CHAT}/_messages`)).json()).filter((c: any) => c.path === new URL(hook).pathname).pop(); return !!card }).toBe(true)
  const content = card.body.attachments[0].content
  expect(JSON.stringify(content.body)).toContain('order A100')
  const approve = content.actions[0].url as string; expect(approve).toContain('/approve?token=a.')

  await page.goto(approve)
  await expect(page.locator('#approve-card')).toContainText(vt('approve.approveQ')); await expect(page.locator('#approve-card')).toContainText('Approve refund for order A100?')
  await page.locator('#approve-confirm').click(); await expect(page.locator('#approve-done')).toBeVisible()
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: H })).json()).data[0].status, { timeout: 30_000 }).toBe('ok')

  await page.reload(); await expect(page.locator('#approve-decided')).toContainText('admin@example.com'); await expect(page.locator('#approve-confirm')).toHaveCount(0)
})
