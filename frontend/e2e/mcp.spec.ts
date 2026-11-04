import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import path from 'path'
// TASK-0013: register a stdio MCP server (the demo fixture), discover its tools, use one in an MCP tool node.
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}
const n = (id: string, type: string, x: number, y: number, data: any = {}) => ({ id, type, position: { x, y }, data: { label: id, ...data } })
const e = (s: string, t: string) => ({ id: `${s}-${t}`, source: s, target: t })
const FIX = path.resolve('../backend/tests/fixtures/mcp_demo_server.py')  // cwd: frontend/
const PY = process.env.E2E_PYTHON || path.resolve('../backend/.venv/bin/python')

test('MCP server: register, discover, run a tool node', async ({ page }) => {
  const auth = await login(page); const name = `Demo MCP ${Date.now()}`
  await page.goto('/settings/mcp')
  await expect(page.locator('#mcp-sandbox-note')).toContainText('stdio')
  await page.locator('#mcp-add').click(); await page.locator('#mcp-new-name').fill(name)
  await page.locator('#mcp-new-transport').click(); await page.getByRole('option', { name: 'stdio (lệnh cục bộ)' }).click()
  await page.locator('#mcp-new-command').fill(PY); await page.locator('#mcp-new-args').fill(FIX)
  await page.locator('#mcp-new-add-secret').click()
  await page.getByTestId('mcp-secret').getByLabel('Tên').fill('API_TOKEN'); await page.getByTestId('mcp-secret').getByLabel('Giá trị').fill('s3cret-value')
  await page.locator('#mcp-create').click()
  const card = page.locator('[data-testid^="mcp-card-"]', { hasText: name })
  await expect(card).toContainText('API_TOKEN ••••alue'); await expect(card).not.toContainText('s3cret')
  await card.locator('[id$="-discover"]').click()
  await expect(card.getByTestId('mcp-tools')).toContainText('add'); await expect(card.getByTestId('mcp-tool-count')).toContainText('5')
  const srv = (await (await page.request.get('/api/mcp/servers', { headers: auth })).json()).data.servers.find((s: any) => s.name === name)
  const WF = { name: `MCP ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'n', type: 'integer' }, { name: 'sum', type: 'object' }],
    nodes: [n('start', 'start', 40, 120), n('m', 'mcp', 300, 120, { label: 'Add numbers', server_id: srv.id, tool: 'add', arguments: { a: '{{state.n}}', b: '2' }, output_field: 'sum' }), n('end', 'end', 560, 120)],
    edges: [e('start', 'm'), e('m', 'end')] }
  const saved = (await (await page.request.post('/api/workflows', { headers: auth, data: WF })).json()).data
  expect(saved.errors).toEqual([])
  await page.goto(`/workflows/${saved.id}`)
  await expect(page.getByText('Gọi công cụ trên máy chủ MCP')).toBeVisible()
  await page.locator('.react-flow__node[data-id="m"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#mcp-server')).toContainText(name); await expect(page.locator('#mcp-tool')).toContainText('add')
  await expect(page.locator('#mcp-arg-a .template-tag[data-field="n"]')).toBeVisible(); await expect(page.locator('#mcp-tool-desc')).toContainText('Add two integers')
  await page.locator('#run-input').fill('{"message": "hi", "n": 40}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  const run = (await (await page.request.get(`/api/workflows/${saved.id}/runs`, { headers: auth })).json()).data[0]
  expect(run.final_state.sum).toEqual({ sum: 42 })  // n kept its type; the form string '2' was coerced to an integer
})
