import { test, expect, type Page } from '@playwright/test'
import { login, N } from './helpers'
// TASK-0189 (REQ-0081): AI review of approvals in en and vi. The judge is an Ollama credential on the fake API of
// backend/tests/fixtures/mock_chat_api.py, which answers approve with 0.92. Suggest mode: the opinion shows in the
// Approvals inbox, a person answers, the agreement rate counts it, and the workflow can be paused there.
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
const SHOTS = process.env.E2E_SHOTS  // a directory: also save review screenshots (r010-auto-*.png)
const shot = async (page: Page, name: string, lang: string) => { if (SHOTS) await page.screenshot({ path: `${SHOTS}/r010-auto-${name}-${lang}.png`, fullPage: true }) }

const REFUND = { name: 'send_refund', description: 'Refund an order', source: 'http', method: 'POST', url: 'https://pay.example/refund', approval: true,
  parameters: { type: 'object', properties: { order: { type: 'string' }, amount: { type: 'number' } }, required: ['order', 'amount'] } }
const policy = (cred: string, mode: string) => ({ mode, min_confidence: 0.8, max_per_day: 50, notify: true,
  judge: { credential_id: cred, model: 'llama3.2:latest', instructions: 'Refunds up to 50 USD are fine.' },
  rules: [{ field: 'args.amount', op: 'gt', value: 100, effect: 'human' }] })
const WF = (name: string, cred: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }, { name: 'answer', type: 'string' }],
  nodes: [N('s', 'start', 40), N('ask', 'human', 260, { label: 'Refund approval', prompt: 'Refund 20 USD for {{state.message}}?', output_field: 'decision', approval: { auto: policy(cred, 'suggest') } }),
    N('ag', 'agent', 480, { label: 'Refunds', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'answer', max_rounds: 3, tools: [REFUND], approval: { auto: policy(cred, 'auto') } }, 300),
    N('e', 'end', 700)],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'ag' }, { id: '3', source: 'ag', target: 'e' }] })

const TEXT = {
  en: { section: 'AI review', suggest: 'Suggests approve', panel: 'AI review', agreement: 'Agreement 100%' },
  vi: { section: 'AI duyệt', suggest: 'Gợi ý duyệt', panel: 'AI duyệt', agreement: 'Đồng ý 100%' },
}

for (const lang of ['en', 'vi'] as const) {
  test.describe(lang, () => {
    test(`AI review settings, the opinion in the inbox, agreement and pause (${lang})`, async ({ page }) => {
      const T = TEXT[lang]; const H = await login(page)
      await page.evaluate(l => localStorage.setItem('lang', l), lang)  // the UI language the next pages load in
      const cred = (await (await page.request.post('/api/credentials', { headers: H, data: { name: `judge-${lang}-${Date.now()}`, provider: 'ollama', base_url: `${CHAT}/ollama` } })).json()).data
      const name = `AI review ${lang} ${Date.now()}`
      const wid = (await (await page.request.post('/api/workflows', { headers: H, data: WF(name, cred.id) })).json()).data.id

      // the Human node: suggest mode with the judge, limits and one rule
      await page.goto(`/workflows/${wid}`)
      await page.locator('.react-flow__node[data-id="ask"]').click()
      const human = page.locator('#human-auto'); await human.scrollIntoViewIfNeeded()
      await expect(human).toContainText(T.section)
      await expect(page.locator('#human-auto-credential')).toContainText(cred.name)
      await expect(page.locator('#human-auto-min')).toHaveValue('0.8'); await expect(page.locator('#human-auto-cap')).toHaveValue('50')
      await expect(human.getByTestId('auto-rule')).toHaveCount(1)
      await expect(page.locator('#human-auto-owner-only')).toHaveCount(0)  // the owner (admin) may choose auto
      await shot(page, 'human', lang)

      // the Agent node's tool approval: auto mode
      await page.locator('.react-flow__node[data-id="ag"]').click()
      const agent = page.locator('#agent-auto'); await agent.scrollIntoViewIfNeeded()
      await expect(agent).toContainText(T.section); await expect(page.locator('#agent-auto-notify')).toBeVisible()
      await shot(page, 'agent', lang)

      // a run waits at the Human node; the opinion shows in the inbox
      await page.locator('.react-flow__node[data-id="ask"]').click()
      await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "order A100"}')
      await page.locator('#run-btn').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
      await page.goto('/approvals')
      const row = page.locator(`[data-testid="inbox-row"]`).filter({ hasText: name })
      await expect(row.getByTestId('inbox-ai')).toBeVisible({ timeout: 30_000 })
      await expect(row.getByTestId('inbox-ai-decision')).toHaveText(T.suggest)
      await expect(row.getByTestId('inbox-ai')).toContainText('92%')
      await shot(page, 'inbox', lang)

      // a person approves: they agreed with the AI
      await row.getByTestId('answer-approve').click()
      await expect(page.locator('#inbox-sent')).toBeVisible()
      await page.reload()
      const panel = page.locator('#ai-review'); await expect(panel).toContainText(T.panel)
      const mine = panel.locator(`[data-workflow="${wid}"]`)
      await expect(mine.getByTestId('ai-review-agreement')).toHaveText(T.agreement)
      await expect(page.locator('#ai-review-org')).toBeVisible()  // admin: the organisation switch

      // pause this workflow: kept on reload, and the editor says so
      await page.locator(`#ai-review-pause-${wid}`).click()
      await expect(page.locator(`#ai-review-pause-${wid}`)).toHaveAttribute('data-state', 'checked')
      await mine.scrollIntoViewIfNeeded(); await shot(page, 'approvals', lang)
      await page.reload(); await expect(page.locator(`#ai-review-pause-${wid}`)).toHaveAttribute('data-state', 'checked')
      await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="ask"]').click()
      await expect(page.locator('#human-auto-paused')).toBeVisible()
      await page.request.put(`/api/approvals/auto/workflows/${wid}`, { headers: H, data: { paused: false } })
    })
  })
}
