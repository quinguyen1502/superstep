import { test, expect, type Page } from '@playwright/test'
import { apiToken, newWorkflow, N } from './helpers'
// REQ-0078 (TASK-0182): Triage hands off to Billing or Technical. The canvas shows the targets as dashed links, the
// Agent's Config lists them, a link deleted on the canvas removes the target and the menu adds it back. In the studio
// chat the offline model hands a refund question to Billing, and the steps show the hand-off.
const shot = async (page: Page, name: string, sel = 'body') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const STATE = [{ name: 'message', type: 'string' }, { name: 'reply', type: 'string' }]
const TOOL = { name: 'lookup_order', description: 'Find the status of an order', source: 'builtin', function: 'lookup_order' }
const agent = (id: string, label: string, x: number, y: number, handoffs?: unknown) =>
  N(id, 'agent', x, { label, model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'reply', tools: [TOOL], ...(handoffs ? { handoffs } : {}) }, y)
const DESK = (name: string, T: typeof TEXT['en']) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40, {}, 160), agent('triage', 'Triage', 280, 160, [{ target: 'billing', description: T.billing }, { target: 'tech', description: T.tech }]),
    agent('billing', 'Billing', 560, 40), agent('tech', T.techLabel, 560, 300), N('e', 'end', 840, {}, 160)],
  edges: [{ id: '1', source: 's', target: 'triage' }, { id: '2', source: 'triage', target: 'e' }, { id: '3', source: 'billing', target: 'e' }, { id: '4', source: 'tech', target: 'e' }] })
const TEXT = {
  en: { billing: 'Duplicate charges, refunds and invoices', tech: 'Crashes, bugs and errors', techLabel: 'Technical', ask: 'I want a refund for a duplicate charge', to: 'to Billing', title: 'Hand-offs' },
  vi: { billing: 'Duplicate charges, refunds and invoices', tech: 'Crashes, bugs and errors', techLabel: 'Kỹ thuật', ask: 'I want a refund for a duplicate charge', to: 'cho Billing', title: 'Chuyển giao' },
}

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', viewport: { width: 1600, height: 1500 } })   // tall: the whole Config panel in one shot

  test(`hand-offs on the canvas, in Config and in the chat (${lang})`, async ({ page }) => {
    const T = TEXT[lang]
    await page.goto('/login'); await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
    await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }; const n = Date.now() % 100000
    const wid = await newWorkflow(page, H, DESK(`Help desk ${lang} ${n}`, T))
    expect((await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, input_field: 'message', reply_field: 'reply' } })).ok()).toBeTruthy()

    await page.goto(`/workflows/${wid}`)
    const links = page.locator('.react-flow__edge.handoff-edge')
    await expect(links).toHaveCount(2)
    await expect(page.getByTestId('handoff-handle')).toHaveCount(3)
    await shot(page, `r010-handoff-canvas-${lang}`, '.react-flow')

    // Config: the targets with their descriptions; remove one, then add it back from the menu
    await page.locator('.react-flow__node').filter({ hasText: 'Triage' }).click()
    await expect(page.locator('#agent-handoffs')).toContainText(T.title)
    await expect(page.getByTestId('agent-handoff')).toHaveCount(2)
    await page.locator('#agent-handoff-remove-tech').click()
    await expect(links).toHaveCount(1)
    await page.locator('#agent-add-handoff').click(); await page.locator('#agent-handoff-pick-tech').click()
    await page.locator('#agent-handoff-desc-tech').fill(T.tech)
    await expect(links).toHaveCount(2)
    await page.locator('#agent-handoffs').scrollIntoViewIfNeeded(); await shot(page, `r010-handoff-config-${lang}`, '#config-panel')
    await page.keyboard.press('Control+s')

    // the studio chat: the offline model hands the refund question to Billing
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await expect(page.locator('#chat-view')).toBeVisible()
    await page.locator('#chat-input').fill(T.ask); await page.keyboard.press('Enter')
    await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await expect(page.getByTestId('chat-step-handoff').first()).toContainText(T.to)
    await shot(page, `r010-handoff-chat-trace-${lang}`, '#chat-panel')
  })
})
