import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// follow-up: live LLM text in the trace, Ollama embeddings for a knowledge base, credential edit in place.
// Fake Ollama / OpenRouter live in backend/tests/fixtures/mock_chat_api.py (streamed chat with a delay per chunk).
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}
const n = (id: string, type: string, x: number, data: any = {}) => ({ id, type, position: { x, y: 120 }, data: { label: id, ...data } })

test('LLM node output streams into the run trace, final text unchanged', async ({ page }) => {
  const auth = await login(page)
  const cred = (await (await page.request.post('/api/credentials', { headers: auth, data: { name: `stream-${Date.now()}`, provider: 'ollama', base_url: `${CHAT}/ollama` } })).json()).data
  const WF = { name: `Stream ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
    nodes: [n('start', 'start', 40), n('talk', 'llm', 280, { label: 'Talk', credential_id: cred.id, model: 'llama3.2:latest', prompt: 'Trả lời: {{state.message}}', output_field: 'answer' }), n('end', 'end', 520)],
    edges: [{ id: 'a', source: 'start', target: 'talk' }, { id: 'b', source: 'talk', target: 'end' }] }
  const wf = (await (await page.request.post('/api/workflows', { headers: auth, data: WF })).json()).data
  await page.goto(`/workflows/${wf.id}`); await page.locator('#run-btn').click()
  const live = page.getByTestId('span-live')
  await expect(live).toContainText('xin chào', { timeout: 15_000 })           // partial text while the node runs
  await expect(live).not.toContainText('từng phần.')
  await page.locator('[data-span="talk#1"]').click(); await expect(page.locator('#trace-live')).toBeVisible()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 15_000 })
  await expect(live).toHaveCount(0)
  const run = (await (await page.request.get(`/api/workflows/${wf.id}/runs`, { headers: auth })).json()).data[0]
  expect(run.final_state.answer).toBe('[ollama:llama3.2:latest] xin chào, đây là câu trả lời từng phần.')
  expect(run.events.some((e: any) => e.type === 'node_token')).toBe(false)  // live text is not stored
})

test('knowledge base with Ollama embeddings: default model, test, dims badge, search', async ({ page }) => {
  const auth = await login(page); const tag = Date.now()
  await page.request.post('/api/credentials', { headers: auth, data: { name: `emb-${tag}`, provider: 'ollama', base_url: `${CHAT}/ollama` } })
  await page.request.post('/api/credentials', { headers: auth, data: { name: `ant-${tag}`, provider: 'anthropic', api_key: 'sk-ant-e2e' } })
  await page.goto('/settings/knowledge'); await page.locator('#kb-add').click()
  await page.locator('#kb-new-name').fill(`Local KB ${tag}`)
  await page.locator('#kb-new-credential').click()
  await expect(page.getByRole('option', { name: new RegExp(`ant-${tag}`) })).toHaveCount(0)  // Anthropic has no embeddings
  await page.getByRole('option', { name: new RegExp(`emb-${tag}`) }).click()
  await expect(page.locator('#kb-new-model')).toHaveValue('nomic-embed-text')
  await page.locator('#kb-new-embed-test').click(); await expect(page.locator('#kb-new-embed-ok')).toContainText('8 chiều')
  await page.locator('#kb-new-model').fill('llama3.2:latest'); await page.locator('#kb-new-embed-test').click()
  await expect(page.locator('#kb-new-embed-error')).toContainText('llama3.2:latest')                // MODEL_NOT_FOUND
  await page.locator('#kb-new-model').fill('nomic-embed-text'); await page.locator('#kb-create').click()
  const card = page.locator('[data-testid^="kb-card-"]', { hasText: `Local KB ${tag}` })
  await card.locator('input[type=file]').setInputFiles({ name: 'faq.md', mimeType: 'text/markdown', buffer: Buffer.from('Hoàn tiền trong bảy ngày.\n\nGiao hàng hai ngày.') })
  await expect(card.getByTestId('kb-dims')).toContainText('8 chiều')
  await expect(card).toContainText('ollama:nomic-embed-text')
  await card.locator('[id$="-query"]').fill('hoàn tiền'); await card.locator('[id$="-search"]').click()
  await expect(card.getByTestId('kb-hits')).toContainText('faq.md')
})

test('edit a credential in place: secret kept unless re-entered', async ({ page }) => {
  const auth = await login(page); const name = `or-${Date.now()}`
  await page.request.post('/api/credentials', { headers: auth, data: { name, provider: 'openrouter', api_key: 'sk-or-good', base_url: `${CHAT}/openrouter/api/v1` } })
  await page.locator('#creds-btn').click(); const dlg = page.getByRole('dialog')
  await dlg.getByRole('button', { name: `Sửa ${name}` }).click()
  await expect(dlg.locator('#cred-form')).toHaveAttribute('data-mode', 'edit')
  await expect(dlg.locator('#cred-provider')).toBeDisabled()
  await expect(dlg.locator('#cred-key')).toHaveValue(''); await expect(dlg.locator('#cred-key')).toHaveAttribute('placeholder', /••••good/)
  await dlg.locator('#cred-test').click(); await expect(dlg.locator('#cred-test-result')).toContainText('Đã kết nối · 2 model')  // stored key used
  await dlg.locator('#cred-name').fill(`${name}-team`); await dlg.locator('#cred-h-X-Title').fill('Studio')
  await dlg.locator('#cred-save').click()
  const row = dlg.locator(`[data-cred="${name}-team"]`)
  await expect(row).toContainText('••••good'); await expect(dlg.locator('#cred-form')).toHaveAttribute('data-mode', 'add')
  await row.getByRole('button', { name: `Kiểm tra kết nối ${name}-team` }).click(); await expect(row).toContainText('Đã kết nối')
  await row.getByRole('button', { name: `Sửa ${name}-team` }).click()
  await dlg.locator('#cred-key').fill('sk-or-bad-0000'); await dlg.locator('#cred-save').click()
  await expect(row).toContainText('••••0000')
  await row.getByRole('button', { name: `Kiểm tra kết nối ${name}-team` }).click(); await expect(row).toContainText('từ chối API key')
})
