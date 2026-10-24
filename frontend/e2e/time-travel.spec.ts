import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// Time travel: list a finished run's checkpoints, inspect and edit a state, fork a new run from there.
const APPROVAL = {
  name: `Time travel e2e ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 260, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve?', output_field: 'decision' } },
    { id: 'route', type: 'condition', position: { x: 500, y: 150 }, data: { label: 'Approved?', field: 'decision', default: 'rejected' } },
    { id: 'e', type: 'end', position: { x: 740, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'route' },
    { id: '3', source: 'route', target: 'e', label: 'approved' }, { id: '4', source: 'route', target: 'e', label: 'rejected' }],
}
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}

test('time travel: inspect checkpoints, edit the state and fork', async ({ page }) => {
  const H = await login(page)
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: APPROVAL })).json()).data.id
  await page.goto(`/workflows/${wid}`); await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"message": "order A100"}'); await page.locator('#run-btn').click()
  await page.locator('#human-approve').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  const first = (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: H })).json()).data[0]
  await page.locator('#trace-time-travel').click()
  const cps = page.locator('#time-travel-dialog [data-testid=checkpoint]')
  await expect(cps).toHaveCount(3)
  await expect(cps.nth(0)).toContainText('Manager approval'); await expect(cps.nth(2)).toContainText('State cuối')
  await cps.nth(2).click(); await expect(page.locator('#time-travel-fork')).toBeDisabled()  // the final state: inspect only
  await cps.nth(1).click(); await expect(page.locator('#checkpoint-state')).toContainText('"decision": "approved"')
  await page.locator('#checkpoint-state').fill(JSON.stringify({ message: 'order A100', decision: 'rejected' }))
  await expect(page.locator('#time-travel-edited')).toBeVisible()
  await page.locator('#time-travel-fork').click()
  await expect(page.locator('#time-travel-dialog')).toHaveCount(0)
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(page.locator('#trace-forked-from')).toContainText(first.id)
  const runs = (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: H })).json()).data
  const forked = runs.find((r: any) => r.id !== first.id)
  expect(forked.final_state.decision).toBe('rejected'); expect(forked.events[0].forked_from).toMatchObject({ run_id: first.id, checkpoint: 1, edited: true })
  expect(forked.events.filter((e: any) => e.type === 'node_finished').map((e: any) => e.node)).not.toContain('ask')
})
