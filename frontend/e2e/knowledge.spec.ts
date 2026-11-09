import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// knowledge base management (create, upload, test search) and a Retriever node in a run.
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}
const n = (id: string, type: string, x: number, y: number, data: any = {}) => ({ id, type, position: { x, y }, data: { label: id, ...data } })
const e = (s: string, t: string) => ({ id: `${s}-${t}`, source: s, target: t })
const FAQ = 'Giao hàng\n\nĐơn hàng được giao trong hai ngày làm việc từ kho Hà Nội.\n\nHoàn tiền\n\nTiền được hoàn về thẻ trong 7 ngày sau khi nhận hàng trả lại.'

test('knowledge base: upload, search, Retriever node', async ({ page }) => {
  const auth = await login(page); const name = `FAQ ${Date.now()}`
  await page.goto('/settings/knowledge')
  await page.locator('#kb-add').click(); await page.locator('#kb-new-name').fill(name); await page.locator('#kb-create').click()
  const card = page.locator('[data-testid^="kb-card-"]', { hasText: name })
  await expect(card).toBeVisible(); await expect(card.getByTestId('kb-empty')).toBeVisible()
  await card.locator('input[type=file]').setInputFiles({ name: 'faq.md', mimeType: 'text/markdown', buffer: Buffer.from(FAQ) })
  await expect(card.getByTestId('kb-file')).toContainText('faq.md'); await expect(card.getByTestId('kb-docs')).toContainText('1 tài liệu')
  await card.locator('input[type=file]').setInputFiles({ name: 'x.docx', mimeType: 'application/octet-stream', buffer: Buffer.from('x') })
  await expect(card.getByRole('alert')).toContainText('Loại tệp không được hỗ trợ')
  await card.locator('[id$="-query"]').fill('hoàn tiền về thẻ'); await card.locator('[id$="-search"]').click()
  await expect(card.getByTestId('kb-hits')).toContainText('faq.md')
  const kb = (await (await page.request.get('/api/knowledge-bases', { headers: auth })).json()).data.find((k: any) => k.name === name)
  expect(kb.embedder).toBe('mock:512')
  const WF = { name: `RAG ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'context', type: 'list' }, { name: 'answer', type: 'string' }],
    nodes: [n('start', 'start', 40, 120), n('ret', 'retriever', 280, 120, { label: 'Tìm FAQ', knowledge_base_id: kb.id, query: '{{state.message}}', top_k: 2, output_field: 'context' }),
      n('llm', 'llm', 520, 120, { model: 'gpt-4o-mini', prompt: 'Dựa vào {{state.context}} trả lời {{state.message}}', output_field: 'answer' }), n('end', 'end', 760, 120)],
    edges: [e('start', 'ret'), e('ret', 'llm'), e('llm', 'end')] }
  const saved = (await (await page.request.post('/api/workflows', { headers: auth, data: WF })).json()).data
  expect(saved.errors).toEqual([])
  await page.goto(`/workflows/${saved.id}`)
  await expect(page.getByText('Tìm trong kho tri thức')).toBeVisible()
  await page.locator('.react-flow__node[data-id="ret"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#retriever-kb')).toContainText(name); await expect(page.locator('#retriever-topk')).toHaveValue('2')
  await expect(page.locator('#retriever-manage')).toHaveAttribute('href', '/settings/knowledge')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  const run = (await (await page.request.get(`/api/workflows/${saved.id}/runs`, { headers: auth })).json()).data[0]
  expect(run.final_state.context[0].filename).toBe('faq.md')
})
