// The offline mock model and the example tools answer in the UI language: the studio sends it with every run.
import { test, expect } from '@playwright/test'
import { apiToken, login, newWorkflow, N } from './helpers'

const WF = {
  name: 'Mock locale', state: [{ name: 'message', type: 'string' }, { name: 'order', type: 'string' }, { name: 'answer', type: 'string' }],
  nodes: [N('start', 'start', 40), N('lookup', 'tool', 260, { mode: 'function', function: 'lookup_order', output_field: 'order' }),
    N('reply', 'llm', 480, { model: 'gpt-4o-mini', prompt: 'Order: {{state.order}}', output_field: 'answer' }), N('end', 'end', 700)],
  edges: [{ id: '1', source: 'start', target: 'lookup' }, { id: '2', source: 'lookup', target: 'reply' }, { id: '3', source: 'reply', target: 'end' }],
}

test('mock answers follow the UI language (en, vi)', async ({ page }) => {
  const H = { Authorization: `Bearer ${await apiToken(page)}` }
  const id = await newWorkflow(page, H, WF)
  await login(page)
  const last = async () => (await (await page.request.get(`/api/workflows/${id}/runs`, { headers: H })).json()).data[0].final_state
  for (const [lang, answer] of [['en', '[mock:gpt-4o-mini] Answer: Order: Order A100: Delivered on 2026-10-10'],
                                ['vi', '[mock:gpt-4o-mini] Trả lời: Order: Đơn A100: Đã giao hàng (delivered) ngày 2026-10-10']] as const) {
    await page.evaluate(l => localStorage.setItem('lang', l), lang)
    await page.goto(`/workflows/${id}`); await expect(page.locator('.react-flow__node')).toHaveCount(4)
    await page.locator('#run-tab').click()
    await page.locator('#run-input').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText('{"message": "Where is A100?"}')
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    expect((await last()).answer).toBe(answer)
  }
})
