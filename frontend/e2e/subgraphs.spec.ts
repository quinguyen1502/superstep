import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// parallel branches + Join with an append reducer, and a Subgraph node running another saved workflow.
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}
const n = (id: string, type: string, x: number, y: number, data: any = {}) => ({ id, type, position: { x, y }, data: { label: id, ...data } })
const e = (s: string, t: string) => ({ id: `${s}-${t}`, source: s, target: t })
const llm = (id: string, x: number, y: number, out: string, prompt = 'Say {{state.message}}') => n(id, 'llm', x, y, { model: 'gpt-4o-mini', prompt, output_field: out })
const stamp = Date.now()
const CHILD = { name: `Summarise ${stamp}`, state: [{ name: 'message', type: 'string' }, { name: 'summary', type: 'string' }],
  nodes: [n('s', 'start', 40, 120), llm('sum', 260, 120, 'summary', 'Summarise {{state.message}}'), n('e', 'end', 480, 120)], edges: [e('s', 'sum'), e('sum', 'e')] }

test('parallel branches, Join and a Subgraph node', async ({ page }) => {
  const auth = await login(page)
  const child = (await (await page.request.post('/api/workflows', { headers: auth, data: CHILD })).json()).data.id
  const PARENT = { name: `Research ${stamp}`, state: [{ name: 'message', type: 'string' }, { name: 'notes', type: 'list', reducer: 'append' }, { name: 'answer', type: 'string' }],
    nodes: [n('start', 'start', 40, 200), llm('web', 280, 80, 'notes'), llm('docs', 280, 320, 'notes'), n('join', 'join', 520, 200, { label: 'All notes' }),
      n('sub', 'subgraph', 740, 200, { label: 'Summary', workflow_id: child }), llm('reply', 980, 200, 'answer', 'Reply {{state.summary}}'), n('end', 'end', 1220, 200)],
    edges: [e('start', 'web'), e('start', 'docs'), e('web', 'join'), e('docs', 'join'), e('join', 'sub'), e('sub', 'reply'), e('reply', 'end')] }
  const saved = (await (await page.request.post('/api/workflows', { headers: auth, data: PARENT })).json()).data
  expect(saved.errors).toEqual([])
  await page.goto(`/workflows/${saved.id}`)
  // palette has the new node types; the state schema shows the reducer
  await expect(page.getByText('Chờ mọi nhánh song song')).toBeVisible(); await expect(page.getByText('Chạy một workflow đã lưu')).toBeVisible()
  await page.locator('#palette-state-tab').click()
  await expect(page.locator('#reducer-notes')).toContainText('Nối (gom tất cả)')
  // subgraph settings: the chosen workflow, open link
  await page.locator('.react-flow__node[data-id="sub"]').click()
  await page.locator('#config-tab-settings').click()
  await expect(page.locator('#subgraph-workflow')).toContainText(CHILD.name)
  await expect(page.locator('#subgraph-open')).toHaveAttribute('href', `/workflows/${child}`)
  await page.locator('.react-flow__node[data-id="join"]').click(); await page.locator('#config-tab-settings').click(); await expect(page.locator('#join-hint')).toBeVisible()
  // run: both branches, the join once, the inner node of the subgraph in the trace, subgraph node marked done
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  for (const k of ['web#1', 'docs#1', 'join#1', 'sub/sum#1']) await expect(page.locator(`.trace-row[data-span="${k}"]`)).toHaveCount(1)
  await expect(page.locator('.trace-row[data-span="sub/sum#1"]')).toContainText('Summary › sum')
  await expect(page.locator('.react-flow__node[data-id="sub"]')).toContainText(/xong/i)
  const run = (await (await page.request.get(`/api/workflows/${saved.id}/runs`, { headers: auth })).json()).data[0]
  expect(run.final_state.notes).toHaveLength(2); expect(run.final_state.summary).toBeTruthy()
  // a parallel write without a reducer is reported on save
  await page.locator('#reducer-notes').click(); await page.getByRole('option', { name: 'Thay thế (giữ giá trị ghi sau cùng)' }).click()
  await page.getByRole('button', { name: 'Lưu', exact: true }).click()
  await expect(page.locator('#validation-errors')).toContainText('state.notes')
})
