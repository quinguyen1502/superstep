import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'

async function admin(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return apiToken(page)
}
const slow = (n: number, name: string) => {
  const ids = ['s', ...Array.from({ length: n }, (_, i) => `wait${i + 1}`), 'e']
  return { name, state: [{ name: 'message', type: 'string' }, { name: 'out', type: 'string' }],
    nodes: ids.map((id, i) => ({ id, type: i === 0 ? 'start' : i === ids.length - 1 ? 'end' : 'tool', position: { x: 40 + i * 220, y: 180 },
      data: i === 0 ? { label: 'Start' } : i === ids.length - 1 ? { label: 'End' } : { label: `Wait ${i}`, mode: 'function', function: 'sleep_demo', output_field: 'out' } })),
    edges: ids.slice(1).map((id, i) => ({ id: `e${i}`, source: ids[i], target: id })) }
}
async function open(page: Page, token: string | null, wf: object) {
  const r = await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: wf })
  await page.goto(`/workflows/${(await r.json()).data.id}`)
}


test('cancel a running workflow', async ({ page }) => {
  const t = await admin(page); await open(page, t, slow(4, 'Slow demo (cancel)'))
  await page.locator('#run-btn').click()
  await expect(page.locator('#cancel-btn')).toBeVisible()
  await expect(page.locator('.trace-row[data-span="wait1#1"]')).toBeVisible()
  await page.locator('#cancel-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'cancelled', { timeout: 5000 })
  await expect(page.locator('#trace-cancelled')).toBeVisible()
  await expect(page.locator('#cancel-btn')).toHaveCount(0)
  await page.locator('#history-all').click()
  await expect(page.locator('#history-dialog').getByText('đã huỷ').first()).toBeVisible()
})

test('run timeout shows timeout status', async ({ page }) => {
  const t = await admin(page); await open(page, t, slow(6, 'Slow demo (timeout)'))
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'timeout', { timeout: 15000 })
  await expect(page.locator('#trace-run-error')).toContainText('Run vượt quá thời gian cho phép (5s)') // RUN_TIMEOUT translated; seconds from error.details
})

test('validation errors are listed clearly', async ({ page }) => {
  const t = await admin(page)
  await open(page, t, { name: 'Broken graph', state: [{ name: 'message', type: 'string' }],
    nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
      { id: 'a', type: 'llm', position: { x: 260, y: 80 }, data: { label: 'Draft', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
      { id: 'b', type: 'llm', position: { x: 480, y: 80 }, data: { label: 'Refine', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
      { id: 'lonely', type: 'tool', position: { x: 260, y: 300 }, data: { label: 'Unreachable tool', mode: 'function', function: 'lookup_order', output_field: 'message' } },
      { id: 'e', type: 'end', position: { x: 700, y: 150 }, data: { label: 'End' } }],
    edges: [{ id: '1', source: 's', target: 'a' }, { id: '2', source: 'a', target: 'b' }, { id: '3', source: 'b', target: 'a' }, { id: '4', source: 'lonely', target: 'e' }] })
  await page.locator('#run-btn').click()
  await page.locator('#run-tab').click()
  const box = page.locator('#validation-errors')
  await expect(box).toContainText('Vòng lặp không đi qua Condition hay For each') // validator messages by their code (TASK-0132)
  await expect(box).toContainText('Node lonely không đi tới được từ Start')
})
