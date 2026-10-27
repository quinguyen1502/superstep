// Screenshots for the handbook (handbook/docs/<lang>/images/*.png).
// Run: HANDBOOK_SHOTS=1 npm run e2e -- handbook
// The Code node shots need Docker and the studio-code:1 image; they are skipped otherwise.
import { test, expect, type Page } from '@playwright/test'
import { N, signIn } from './helpers'

test.skip(!process.env.HANDBOOK_SHOTS, 'set HANDBOOK_SHOTS=1 to capture handbook screenshots')
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
test.setTimeout(240_000)

type Lang = 'en' | 'vi'
const T = {
  en: {
    digest: 'Release notes digest', support: 'Customer Support', refund: 'Refund approval', normalize: 'Normalize webhook payload',
    start: 'Start', end: 'End', each: 'Each release', summarize: 'Summarize release', compose: 'Compose digest', send: 'Email the team',
    draft: 'Draft reply', approve: 'Manager approval', approved: 'Approved?', notify: 'Send refund email', clean: 'Clean payload',
    approvePrompt: 'Approve a refund of {{state.amount}} for order {{state.order_id}}?',
    morning: 'Morning digest', broken: 'Broken graph', refine: 'Refine', lonely: 'Unreachable tool',
    kb: 'Support FAQ', kbDesc: 'Shipping and refund answers', faq: 'Shipping\n\nOrders ship within two business days.\n\nRefunds\n\nRefunds reach the card within 7 days of the return.',
  },
  vi: {
    digest: 'Tổng hợp release notes', support: 'Customer Support', refund: 'Duyệt hoàn tiền', normalize: 'Chuẩn hoá payload webhook',
    start: 'Start', end: 'End', each: 'Từng release', summarize: 'Tóm tắt release', compose: 'Soạn bản tổng hợp', send: 'Gửi email cho team',
    draft: 'Soạn trả lời', approve: 'Quản lý duyệt', approved: 'Đã duyệt?', notify: 'Gửi email hoàn tiền', clean: 'Làm sạch payload',
    approvePrompt: 'Duyệt hoàn {{state.amount}} cho đơn {{state.order_id}}?',
    morning: 'Bản tổng hợp buổi sáng', broken: 'Graph lỗi', refine: 'Chỉnh lại', lonely: 'Tool không tới được',
    kb: 'FAQ hỗ trợ', kbDesc: 'Câu trả lời về giao hàng và hoàn tiền', faq: 'Giao hàng\n\nĐơn hàng được giao trong hai ngày làm việc.\n\nHoàn tiền\n\nTiền được hoàn về thẻ trong 7 ngày sau khi nhận hàng trả lại.',
  },
}

const CODE = `def main(state):
    event = state["payload"]
    print("event:", event["type"])
    return {
        "id": event["id"],
        "type": event["type"].lower(),
        "amount": round(event["amount_cents"] / 100, 2),
    }
`

const digest = (s: typeof T.en) => ({
  name: s.digest,
  state: [{ name: 'releases', type: 'list' }, { name: 'release', type: 'string' }, { name: 'summaries', type: 'list', reducer: 'append' },
    { name: 'digest', type: 'string' }, { name: 'email', type: 'object' }],
  nodes: [N('start', 'start', 40, { label: s.start }, 200),
    N('each', 'foreach', 280, { label: s.each, items_field: 'releases', item_field: 'release', max_items: 20 }, 200),
    N('sum', 'llm', 560, { label: s.summarize, model: 'gpt-4o-mini', prompt: 'Summarize in one line: {{state.release | trim}}', output_field: 'summaries' }, 60),
    N('compose', 'llm', 560, { label: s.compose, model: 'gpt-4o-mini', prompt: 'Write a short digest from {{state.summaries | join("\\n")}}', output_field: 'digest' }, 340),
    N('mail', 'email', 840, { label: s.send, to: 'team@example.com', subject: 'Release digest', body: '{{state.digest}}', format: 'text', output_field: 'email' }, 340),
    N('end', 'end', 1100, { label: s.end }, 340)],
  edges: [{ id: 'a', source: 'start', target: 'each' }, { id: 'b', source: 'each', target: 'sum', label: 'each' }, { id: 'c', source: 'sum', target: 'each' },
    { id: 'd', source: 'each', target: 'compose', label: 'done' }, { id: 'e', source: 'compose', target: 'mail' }, { id: 'f', source: 'mail', target: 'end' }],
})

const refund = (s: typeof T.en) => ({
  name: s.refund,
  state: [{ name: 'order_id', type: 'string' }, { name: 'amount', type: 'string' }, { name: 'reply', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [N('start', 'start', 40, { label: s.start }, 180),
    N('draft', 'llm', 280, { label: s.draft, model: 'gpt-4o-mini', prompt: 'Draft a refund reply for order {{state.order_id}}', output_field: 'reply' }, 180),
    N('ask', 'human', 540, { label: s.approve, prompt: s.approvePrompt, output_field: 'decision', deadline: { after: '1d', remind_every: '4h', on_timeout: 'reject' } }, 180),
    N('route', 'condition', 800, { label: s.approved, field: 'decision', default: 'rejected' }, 180),
    N('mail', 'email', 1060, { label: s.notify, to: 'customer@example.com', subject: 'Your refund', body: '{{state.reply}}', format: 'text' }, 80),
    N('end', 'end', 1060, { label: s.end }, 300)],
  edges: [{ id: 'a', source: 'start', target: 'draft' }, { id: 'b', source: 'draft', target: 'ask' }, { id: 'c', source: 'ask', target: 'route' },
    { id: 'd', source: 'route', target: 'mail', label: 'approved' }, { id: 'e', source: 'route', target: 'end', label: 'rejected' }, { id: 'f', source: 'mail', target: 'end' }],
})

const normalize = (s: typeof T.en) => ({
  name: s.normalize,
  state: [{ name: 'payload', type: 'object' }, { name: 'event', type: 'object' }],
  nodes: [N('start', 'start', 40, { label: s.start }, 160),
    N('clean', 'tool', 320, { label: s.clean, mode: 'code', code: CODE, output_field: 'event' }, 160),
    N('end', 'end', 600, { label: s.end }, 160)],
  edges: [{ id: 'a', source: 'start', target: 'clean' }, { id: 'b', source: 'clean', target: 'end' }],
})

const RELEASES = JSON.stringify({ releases: ['v2.4: streaming tokens in the trace', 'v2.5: For each loops with max_items', 'v2.6: Code mode in a Docker sandbox'] }, null, 2)
const PAYLOAD = JSON.stringify({ payload: { id: 'evt_1042', type: 'ORDER.PAID', amount_cents: 12950 } }, null, 2)

async function shot(page: Page, lang: Lang, name: string) {
  await page.mouse.move(2, 898); await page.waitForTimeout(450)
  await page.screenshot({ path: `../handbook/docs/${lang}/images/${name}.png` })
}
async function setInput(page: Page, json: string) {
  await page.locator('#run-tab').click()
  await page.locator('#run-input').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText(json)
}
async function run(page: Page, status = 'ok') {
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', status, { timeout: 30_000 })
}
async function fit(page: Page) { await page.keyboard.press('Shift+1'); await page.waitForTimeout(500) }

for (const lang of ['en', 'vi'] as Lang[]) {
  test.describe(`handbook ${lang}`, () => {
    test.use({ locale: lang === 'en' ? 'en-US' : 'vi-VN' })

    test(`capture ${lang}`, async ({ page }) => {
      const s = T[lang]
      await page.addInitScript(([l]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', 'light') }, [lang])
      await page.goto('/login'); await expect(page.locator('#auth-submit')).toBeVisible()
      const token = await signIn(page, 'admin@example.com', 'admin123')
      const H = { Authorization: `Bearer ${token}` }
      // Start from a clean list: the other language's run shares this database
      for (const w of (await (await page.request.get('/api/workflows', { headers: H })).json()).data)
        if (w.id !== 'example') await page.request.delete(`/api/workflows/${w.id}?force=true`, { headers: H })
      for (const k of (await (await page.request.get('/api/knowledge-bases', { headers: H })).json()).data)
        await page.request.delete(`/api/knowledge-bases/${k.id}`, { headers: H })
      const make = async (wf: object) => (await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).data.id as string
      const ids = { digest: await make(digest(s)), refund: await make(refund(s)), normalize: await make(normalize(s)) }

      // Hero: the seeded Customer Support graph, after a run
      await page.goto('/workflows/example'); await expect(page.locator('.react-flow__node').first()).toBeVisible(); await fit(page)
      await shot(page, lang, 'editor')
      await setInput(page, JSON.stringify({ message: lang === 'en' ? 'Where is order A100?' : 'Đơn A100 của tôi đang ở đâu?' }, null, 2))
      await run(page)
      await shot(page, lang, 'run-trace')
      await page.locator('.react-flow__node[data-id="classify"]').click(); await expect(page.locator('#trace-diff')).toBeVisible()
      await shot(page, lang, 'trace-detail')

      // For each + LLM + Send email (dry run)
      await page.goto(`/workflows/${ids.digest}`); await expect(page.locator('.react-flow__node')).toHaveCount(6); await fit(page)
      await setInput(page, RELEASES); await run(page)
      await shot(page, lang, 'loop-run')
      await page.locator('.react-flow__node[data-id="mail"]').click()
      await shot(page, lang, 'email-node')

      // Human approval: the run waits
      await page.goto(`/workflows/${ids.refund}`); await expect(page.locator('.react-flow__node')).toHaveCount(6); await fit(page)
      await setInput(page, JSON.stringify({ order_id: 'A100', amount: '$129.50', reply: '', decision: '' }, null, 2))
      await run(page, 'waiting'); await expect(page.locator('#human-question')).toBeVisible()
      await shot(page, lang, 'human-waiting')
      await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#human-deadline').scrollIntoViewIfNeeded()
      await shot(page, lang, 'human-deadline')

      // Approvals inbox with the waiting refund, then the workflow list with its link (TASK-0065)
      await page.goto('/approvals'); await expect(page.locator('[data-testid=inbox-row]').first()).toBeVisible()
      await shot(page, lang, 'approvals')
      await page.goto('/workflows'); await expect(page.locator('#pending-runs')).toBeVisible()
      await shot(page, lang, 'workflows')
      await page.locator('#new-wf').click(); await expect(page.locator('#template-gallery')).toBeVisible()
      await shot(page, lang, 'templates'); await page.keyboard.press('Escape')

      // Workflow tests (TASK-0069): the Leave request template comes with its test cases; Run all with the mock model,
      // the case editor, then a mistake in version 2 shows as a regression against version 1
      const leave = (await (await page.request.post('/api/templates/builtin-leave-request/use', { headers: H, data: { name: lang === 'en' ? 'Leave request' : 'Đơn nghỉ phép' } })).json()).data.id
      const runTests = async () => {
        await page.locator('#tests-tab').click(); await page.locator('#tests-mock').click(); await page.locator('#tests-run-all').click()
        await expect(page.locator('#tests-compare')).toBeVisible({ timeout: 60_000 })
      }
      await page.goto(`/workflows/${leave}`); await expect(page.locator('.react-flow__node')).toHaveCount(5); await fit(page)
      await runTests(); await expect(page.locator('#tests-summary')).toContainText(lang === 'en' ? '2 passed, 0 failed' : '2 đạt, 0 không đạt')
      await shot(page, lang, 'tests')
      await page.getByTestId('test-edit').click(); await expect(page.locator('#test-dialog')).toBeVisible()
      await shot(page, lang, 'test-case'); await page.keyboard.press('Escape')
      // Export to Python (TASK-0072): version 1 in the Code tab, with the Human node's code marked
      await page.locator('#code-tab').click(); await page.locator('.react-flow__node[data-id="manager"]').click()
      await expect(page.locator('.cm-node-mark').first()).toBeVisible()
      await shot(page, lang, 'code-tab')
      const v1 = (await (await page.request.get(`/api/workflows/${leave}`, { headers: H })).json()).data
      v1.nodes.find((n: { id: string }) => n.id === 'manager').data.output_field = 'details'  // the answer now overwrites the details
      await page.request.post('/api/workflows', { headers: H, data: v1 })
      await page.reload(); await expect(page.locator('.react-flow__node')).toHaveCount(5); await fit(page)
      await runTests(); await expect(page.getByTestId('compare-regression')).toBeVisible()
      await shot(page, lang, 'tests-compare')
      await page.goto('/workflows'); await expect(page.locator('#new-wf')).toBeVisible()
      await page.locator('#creds-btn').click(); await page.waitForTimeout(400)
      await shot(page, lang, 'credentials'); await page.keyboard.press('Escape')

      // Editor dialogs on the digest workflow
      await page.goto(`/workflows/${ids.digest}`); await expect(page.locator('.react-flow__node')).toHaveCount(6)
      await page.locator('#more-btn').click(); await page.locator('#api-btn').click(); await page.waitForTimeout(500)
      await shot(page, lang, 'api-trigger'); await page.keyboard.press('Escape')
      await page.locator('#more-btn').click(); await page.locator('#schedules-btn').click(); await expect(page.locator('#schedules-dialog')).toBeVisible()
      await page.locator('#schedule-name').fill(s.morning); await page.locator('#schedule-cron').fill('0 8 * * 1-5')
      await expect(page.locator('#schedule-preview')).toBeVisible()
      await shot(page, lang, 'schedules'); await page.keyboard.press('Escape')
      await page.keyboard.press('ControlOrMeta+k'); await page.keyboard.insertText(lang === 'en' ? 'add' : 'thêm'); await page.waitForTimeout(400)
      await shot(page, lang, 'palette'); await page.keyboard.press('Escape')

      // Versions: rename a node, save, diff v1 and v2
      await page.locator('.react-flow__node[data-id="compose"]').click()
      const label = page.locator('div.space-y-1\\.5', { has: page.getByText(lang === 'en' ? 'Label' : 'Nhãn', { exact: true }) }).locator('input').first()
      {
        await label.fill(`${s.compose} (v2)`); await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
        await page.locator('#more-btn').click(); await page.locator('#versions-btn').click()
        await expect(page.locator('[data-testid=version-row]').first()).toBeVisible(); await page.waitForTimeout(500)
        await shot(page, lang, 'versions'); await page.keyboard.press('Escape')
      }

      // Code mode
      const rt = (await (await page.request.get('/api/meta/runtime', { headers: H })).json()).data
      if (rt.available) {
        await page.goto(`/workflows/${ids.normalize}`); await expect(page.locator('.react-flow__node')).toHaveCount(3); await fit(page)
        await setInput(page, PAYLOAD)
        await page.locator('.react-flow__node[data-id="clean"]').click()
        await page.locator('#code-test').click()
        await expect(page.locator('#code-test-result')).toContainText('order.paid', { timeout: 60_000 })
        await page.locator('#code-test-result').scrollIntoViewIfNeeded()
        await shot(page, lang, 'code-node')
      }

      // Validation errors: a loop with no Condition and an unreachable node
      const broken = { name: s.broken, state: [{ name: 'message', type: 'string' }],
        nodes: [N('start', 'start', 40, { label: s.start }, 160),
          N('draft', 'llm', 280, { label: s.draft, model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' }, 80),
          N('refine', 'llm', 540, { label: s.refine, model: 'gpt-4o-mini', prompt: '{{state.missing}}', output_field: 'message' }, 80),
          N('lonely', 'tool', 280, { label: s.lonely, mode: 'function', function: 'lookup_order', output_field: 'message' }, 300),
          N('end', 'end', 800, { label: s.end }, 160)],
        edges: [{ id: '1', source: 'start', target: 'draft' }, { id: '2', source: 'draft', target: 'refine' }, { id: '3', source: 'refine', target: 'draft' },
          { id: '4', source: 'lonely', target: 'end' }] }
      await page.goto(`/workflows/${await make(broken)}`); await expect(page.locator('.react-flow__node')).toHaveCount(5); await fit(page)
      await page.locator('#run-btn').click(); await page.locator('#run-tab').click()
      await expect(page.locator('#validation-errors')).toBeVisible()
      await shot(page, lang, 'validation')

      // Settings, with one knowledge base so the page is not empty
      const kb = (await (await page.request.post('/api/knowledge-bases', { headers: H, data: { name: s.kb, description: s.kbDesc } })).json()).data
      await page.request.post(`/api/knowledge-bases/${kb.id}/documents`, { headers: H, multipart: { file: { name: 'shipping-faq.md', mimeType: 'text/markdown', buffer: Buffer.from(s.faq) } } })
      for (const sec of ['users', 'knowledge', 'mcp', 'channels', 'profile']) {
        await page.goto(`/settings/${sec}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(400)
        await shot(page, lang, `settings-${sec}`)
      }

      // Chat triggers (TASK-0077): a Slack connection (the fake API) and one trigger on the Leave request, opened for editing.
      // Made after the Channels shot so that one stays empty.
      const team = `T${lang.toUpperCase()}${Date.now().toString(36).toUpperCase()}`
      const ch = (await (await page.request.post('/api/approvals/channels', { headers: H, data: { kind: 'slack', name: 'Acme Slack', bot_token: `xoxb-1-${team}-abcdefgh`, signing_secret: '0123456789abcdef0123456789abcdef' } })).json()).data
      await page.request.post(`/api/workflows/${leave}/chat-triggers`, { headers: H, data: { name: lang === 'en' ? 'Leave requests' : 'Đơn nghỉ phép', channel_id: ch.id, place: 'C0HRLEAVE',
        command: lang === 'en' ? 'leave' : 'nghiphep', input_field: 'message', reply_field: 'decision', enabled: true } })
      await page.goto(`/workflows/${leave}`); await expect(page.locator('.react-flow__node')).toHaveCount(5)
      await page.locator('#more-btn').click(); await page.locator('#chat-triggers-btn').click(); await expect(page.locator('#chat-triggers-dialog')).toBeVisible()
      await page.locator('[data-testid=chat-trigger-row]').getByRole('button', { name: /^(Edit|Sửa) chat trigger/ }).click()
      await expect(page.locator('#chat-trigger-sample')).toBeVisible()
      await shot(page, lang, 'chat-triggers'); await page.keyboard.press('Escape')

      // Chat panel (TASK-0085) and the overview shot for the README: tool call, a visitor confirmation, a TypeScript Code node
      // on the refund branch (not run, so no Docker needed), the run trace below and the Code node's settings on the right
      const tsCode = 'export function main(state: { message: string }) {\n  const order = state.message.match(/[A-Z]\\d+/)?.[0] ?? ""\n  return { order_id: order, reason: "refund" }\n}\n'
      const shop = { name: lang === 'en' ? 'Order assistant' : 'Trợ lý đơn hàng',
        state: [{ name: 'message', type: 'string' }, { name: 'intent', type: 'string' }, { name: 'order', type: 'string' }, { name: 'confirm', type: 'string' }, { name: 'answer', type: 'string' }],
        nodes: [N('start', 'start', 40, { label: s.start }, 200),
          N('classify', 'llm', 250, { label: lang === 'en' ? 'Classify intent' : 'Phân loại ý định', model: 'gpt-4o-mini', prompt: 'Classify: {{state.message}}', output_field: 'intent' }, 200),
          N('route', 'condition', 470, { label: lang === 'en' ? 'Route by intent' : 'Rẽ nhánh theo ý định', field: 'intent', default: 'order_status' }, 200),
          N('lookup', 'tool', 690, { label: lang === 'en' ? 'Lookup order' : 'Tra cứu đơn', mode: 'function', function: 'lookup_order', output_field: 'order' }, 80),
          N('refund', 'tool', 690, { label: lang === 'en' ? 'Parse refund' : 'Đọc yêu cầu hoàn', mode: 'code', language: 'typescript', code: tsCode, output_field: 'order' }, 320),
          N('ask', 'human', 910, { label: lang === 'en' ? 'Confirm with customer' : 'Xác nhận với khách', prompt: lang === 'en' ? 'Is this your order? {{state.order}}' : 'Đây có phải đơn của bạn? {{state.order}}', output_field: 'confirm', answered_by: 'visitor' }, 200),
          N('reply', 'llm', 1130, { label: lang === 'en' ? 'Reply' : 'Trả lời', model: 'gpt-4o-mini', prompt: 'Order: {{state.order}}. Confirmed: {{state.confirm}}', output_field: 'answer' }, 200),
          N('end', 'end', 1350, { label: s.end }, 200)],
        edges: [{ id: '1', source: 'start', target: 'classify' }, { id: '2', source: 'classify', target: 'route' }, { id: '3', source: 'route', target: 'lookup', label: 'order_status' },
          { id: '4', source: 'route', target: 'refund', label: 'refund' }, { id: '5', source: 'lookup', target: 'ask' }, { id: '6', source: 'refund', target: 'ask' },
          { id: '7', source: 'ask', target: 'reply' }, { id: '8', source: 'reply', target: 'end' }] }
      const shopId = await make(shop)
      await page.request.put(`/api/workflows/${shopId}/chat`, { headers: H, data: { enabled: true, steps: 'labels' } })
      await page.goto(`/workflows/${shopId}`); await expect(page.locator('.react-flow__node')).toHaveCount(8)
      const say = async (text: string) => { await page.locator('#chat-input').fill(text); await page.keyboard.press('Enter') }
      if (!(await page.locator('#chat-input').isVisible())) await page.locator('#chat-open').click()
      await say(lang === 'en' ? 'Where is my order A100?' : 'Đơn A100 của tôi đang ở đâu?')
      await expect(page.locator('#chat-confirmation')).toBeVisible({ timeout: 30_000 }); await page.locator('#chat-approve').click()
      await expect(page.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
      await say(lang === 'en' ? 'And order B7?' : 'Còn đơn B7 thì sao?'); await expect(page.locator('#chat-confirmation')).toBeVisible({ timeout: 30_000 })
      await page.locator('.react-flow__pane').click({ position: { x: 20, y: 20 } }); await fit(page)  // Shift+1 on the canvas, not in the chat box
      await shot(page, lang, 'chat-tab')
      await page.locator('#chat-view').click(); await page.locator('#chat-view-visitor').click(); await expect(page.locator('#chat-visitor-banner')).toBeVisible()
      await shot(page, lang, 'chat-visitor')
      await page.locator('#chat-visitor-exit').click()
      await page.locator('#chat-fullscreen').click(); await shot(page, lang, 'chat-fullscreen'); await page.keyboard.press('Escape')
      // overview: a bigger window so canvas, settings, trace and chat all fit
      await page.setViewportSize({ width: 1800, height: 1000 })
      await setInput(page, JSON.stringify({ message: lang === 'en' ? 'Where is my order C3?' : 'Đơn C3 của tôi đang ở đâu?' }, null, 2)); await run(page, 'waiting')
      await page.locator('.react-flow__node[data-id="classify"]').click(); await fit(page)
      await page.mouse.move(2, 998); await page.waitForTimeout(450)
      await page.screenshot({ path: `../handbook/docs/${lang}/images/overview.png` })
      await page.setViewportSize({ width: 1440, height: 900 }); await page.locator('#chat-close').click()

      // Dark theme hero
      await page.evaluate(() => localStorage.setItem('theme', 'dark'))
      await page.addInitScript(() => localStorage.setItem('theme', 'dark'))
      await page.goto(`/workflows/${ids.digest}`); await expect(page.locator('.react-flow__node')).toHaveCount(6); await fit(page)
      await setInput(page, RELEASES); await run(page)
      await shot(page, lang, 'editor-dark')
    })

    // The Agent node (TASK-0120): its settings, a run waiting before request_refund, then the trace after Approve.
    // Run alone with `-g agent`. The policy search tool needs a knowledge base, so it is left out here.
    test(`agent ${lang}`, async ({ page }) => {
      await page.addInitScript(([l]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', 'light') }, [lang])
      await page.goto('/login'); await expect(page.locator('#auth-submit')).toBeVisible()
      const H = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
      const vi = lang === 'vi'
      const wid = (await (await page.request.post('/api/templates/builtin-support-agent/use', { headers: H, data: { name: vi ? 'Agent hỗ trợ khách hàng' : 'Support agent' } })).json()).data.id
      const wf = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
      const agent = wf.nodes.find((n: { type: string }) => n.type === 'agent')
      agent.data.tools = agent.data.tools.filter((t: { source: string }) => t.source !== 'knowledge')
      if (vi) {  // the mock picks the tool whose description shares the most words with the message
        Object.assign(agent.data, { label: 'Agent hỗ trợ', prompt: 'Giúp khách hàng này. Tin nhắn: {{state.message}}',
          system_prompt: 'Bạn là nhân viên hỗ trợ của một cửa hàng online. Dùng các công cụ để tra cứu đơn hàng. Chỉ yêu cầu hoàn tiền khi đơn bị vỡ hoặc giao trễ.' })
        agent.data.tools[0].description = 'Tra cứu trạng thái giao hàng của một đơn'
        agent.data.tools[1].description = 'Yêu cầu hoàn tiền cho đơn hàng bị vỡ hoặc giao trễ'
      }
      expect((await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).success).toBe(true)

      await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(3); await fit(page)
      await page.locator('.react-flow__node[data-id="agent"]').click(); await expect(page.locator('#agent-settings')).toBeVisible()
      await page.locator('#agent-settings').getByText(vi ? 'Công cụ' : 'Tools', { exact: true }).first().scrollIntoViewIfNeeded()
      await shot(page, lang, 'agent-settings')
      await setInput(page, JSON.stringify({ message: vi ? 'Đơn A100 của tôi bị vỡ, cho tôi hoàn tiền' : 'Order A100 arrived broken, please refund it' }, null, 2))
      await run(page, 'waiting'); await expect(page.locator('#human-panel')).toBeVisible()
      await shot(page, lang, 'agent-waiting')
      await page.locator('#human-approve').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
      await shot(page, lang, 'agent-trace')
    })

    // Workflows as Agent tools (TASK-0138, REQ-0073): the Support team template's tool card, a run whose trace shows the
    // order desk's steps under the call, and a run waiting for the refund desk's approval. Run alone with `-g "workflow tools"`.
    test(`workflow tools ${lang}`, async ({ page }) => {
      await page.addInitScript(([l]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', 'light') }, [lang])
      await page.goto('/login'); await expect(page.locator('#auth-submit')).toBeVisible()
      const H = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
      const vi = lang === 'vi'
      const wid = (await (await page.request.post('/api/templates/builtin-support-team/use', { headers: H, data: { name: vi ? 'Đội hỗ trợ' : 'Support team' } })).json()).data.id
      if (vi) {  // the mock picks the tool whose description shares the most words with the message
        const wf = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
        const agent = wf.nodes.find((n: { type: string }) => n.type === 'agent')
        Object.assign(agent.data, { label: 'Điều phối', prompt: 'Giúp khách hàng này. Tin nhắn: {{state.message}}' })
        agent.data.tools[0].description = 'Câu hỏi về đơn hàng đang ở đâu'
        agent.data.tools[1].description = 'Yêu cầu hoàn tiền cho đơn hàng bị vỡ hoặc giao trễ'
        expect((await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).success).toBe(true)
      }
      await page.goto(`/workflows/${wid}`); await expect(page.locator('.react-flow__node')).toHaveCount(3); await fit(page)
      await page.locator('.react-flow__node[data-id="agent"]').click(); await expect(page.locator('#agent-settings')).toBeVisible()
      await page.locator('#agent-tool-0-fields').scrollIntoViewIfNeeded()
      await shot(page, lang, 'workflow-tool-settings')
      await setInput(page, JSON.stringify({ message: vi ? 'Đơn hàng B200 của tôi đang ở đâu?' : 'Where is my order B200?' }, null, 2))
      await run(page); await expect(page.getByTestId('child-steps')).toContainText('lookup_order')
      await shot(page, lang, 'workflow-tool-trace')
      await setInput(page, JSON.stringify({ message: vi ? 'Đơn A100 của tôi bị vỡ, cho tôi hoàn tiền' : 'Order A100 arrived broken, please refund it' }, null, 2))
      await run(page, 'waiting'); await expect(page.locator('#child-wait-panel')).toBeVisible()
      await page.waitForTimeout(2500)  // the refund desk reaches its approval
      await page.goto('/approvals'); await expect(page.locator('[data-testid=inbox-row]').first()).toBeVisible()
      await shot(page, lang, 'workflow-tool-approval')
    })

    // The public chat page (TASK-0144, REQ-0074): the publish settings, the embed snippets, and the page a visitor sees.
    // Run alone with `-g "public chat"`.
    test(`public chat ${lang}`, async ({ page, browser }) => {
      await page.addInitScript(([l]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', 'light') }, [lang])
      await page.goto('/login'); await expect(page.locator('#auth-submit')).toBeVisible()
      const H = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
      const vi = lang === 'vi'
      const wf = { name: vi ? 'Hỗ trợ đơn hàng' : 'Order help', state: [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }],
        nodes: [N('start', 'start', 40), N('bot', 'llm', 300, { label: vi ? 'Trả lời' : 'Reply', model: 'gpt-4o-mini', prompt: 'Answer: {{state.message}}', output_field: 'reply' }), N('end', 'end', 560)],
        edges: [{ id: '1', source: 'start', target: 'bot' }, { id: '2', source: 'bot', target: 'end' }] }
      const wid = (await (await page.request.post('/api/workflows', { headers: H, data: wf })).json()).data.id
      const slug = `${vi ? 'ho-tro' : 'order-help'}-${Date.now() % 10000}`
      await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, access: 'anonymous', slug, title: vi ? 'Hỗ trợ đơn hàng' : 'Order help',
        intro: vi ? 'Hỏi về **đơn hàng** của bạn: đơn đang ở đâu, đổi trả, hoàn tiền.' : 'Ask about **your order**: where it is, returns, refunds.',
        suggestions: vi ? ['Đơn A100 của tôi đang ở đâu?', 'Tôi muốn trả hàng'] : ['Where is my order A100?', 'I want to return an item'], embed_origins: ['https://shop.example.com'] } })
      await page.goto(`/workflows/${wid}`)
      if (!(await page.locator('#chat-input').isVisible())) await page.locator('#chat-open').click()
      await page.locator('#chat-view').click(); await page.locator('#chat-settings-btn').click(); await expect(page.locator('#chat-publish')).toBeVisible()
      await page.locator('#chat-slug').scrollIntoViewIfNeeded(); await shot(page, lang, 'chat-publish')
      await page.locator('#chat-snippet-iframe').scrollIntoViewIfNeeded(); await shot(page, lang, 'chat-embed')
      const ctx = await browser.newContext({ locale: vi ? 'vi-VN' : 'en-US', viewport: { width: 1440, height: 900 }, colorScheme: 'light' })
      const v = await ctx.newPage(); await v.addInitScript(([l]) => localStorage.setItem('lang', l), [lang])
      await v.goto(`/c/${slug}`); await expect(v.getByTestId('chat-suggestion')).toHaveCount(2)
      await shot(v, lang, 'public-chat'); await ctx.close()   // what a visitor sees first: the intro and the suggestions
    })
  })
}
