// The handbook quickstart, done in the UI: build, run, approve, trigger over HTTP, schedule.
// Writes one frame per step (and two phone-*.png at 390x844) plus the box of every control the step uses to scripts/promo/build/frames/<lang>/
// (flow.json) for the intro video, and copies the quickstart screenshots to handbook/docs/<lang>/images/.
// Run: HANDBOOK_SHOTS=1 npm run e2e -- quickstart
import fs from 'node:fs'
import { test, expect, type Locator } from '@playwright/test'
import { signIn } from './helpers'

test.skip(!process.env.HANDBOOK_SHOTS, 'set HANDBOOK_SHOTS=1 to capture the quickstart')
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
test.setTimeout(240_000)

type Lang = 'en' | 'vi'
type Box = [number, number, number, number]
const T = {
  en: {
    name: 'Refund reply', draft: 'Draft reply', approve: 'Approve reply', label: 'Label', output: 'Output field', addField: 'Add field',
    prompt: 'Write a short, polite reply to this customer message: {{state.message}}',
    question: 'Send this reply to the customer?\n\n{{state.reply}}',
    message: 'My order A100 arrived broken. Can I get a refund?', token: 'billing-service', schedule: 'Weekday check', history: 'History', wfName: 'Workflow name',
    refund: 'Order A100 arrived broken, please refund it', kb: 'Refund policy',
  },
  vi: {
    name: 'Trả lời hoàn tiền', draft: 'Soạn trả lời', approve: 'Duyệt trả lời', label: 'Nhãn', output: 'Trường output', addField: 'Thêm trường',
    prompt: 'Viết một câu trả lời ngắn, lịch sự cho tin nhắn của khách: {{state.message}}',
    question: 'Gửi câu trả lời này cho khách?\n\n{{state.reply}}',
    message: 'Đơn A100 của tôi bị vỡ khi nhận. Tôi được hoàn tiền không?', token: 'billing-service', schedule: 'Kiểm tra ngày thường', history: 'Lịch sử', wfName: 'Tên workflow',
    refund: 'Order A100 arrived broken, please refund it',  // the template's tools are in English: the mock agent picks one by shared words
    kb: 'Chính sách hoàn tiền',
  },
}
// Frames that also illustrate the quickstart page
const DOC = { gallery: 'quickstart-gallery', graph: 'quickstart-graph', 'llm-config': 'quickstart-llm', 'human-slack': 'quickstart-human', waiting: 'quickstart-waiting', diff: 'quickstart-diff', token: 'quickstart-api', history: 'quickstart-history' }

for (const lang of ['en', 'vi'] as Lang[]) {
  test.describe(`quickstart ${lang}`, () => {
    test.use({ locale: lang === 'en' ? 'en-US' : 'vi-VN' })

    test(`capture ${lang}`, async ({ page, browser }) => {
      const s = T[lang]
      const dir = `../scripts/promo/build/frames/${lang}`
      fs.mkdirSync(dir, { recursive: true })
      const frames: Record<string, { targets: Record<string, Box> }> = {}
      const box = async (l: Locator): Promise<Box> => { const b = (await l.boundingBox())!; return [b.x, b.y, b.width, b.height].map(v => Math.round(v * 10) / 10) as Box }
      // One frame: the screen as it is, and where the controls the next action uses are
      const snap = async (name: string, targets: Record<string, Locator | Box> = {}) => {
        await page.mouse.move(2, 898); await page.waitForTimeout(450)
        await page.screenshot({ path: `${dir}/${name}.png` })
        const t: Record<string, Box> = {}
        for (const [k, v] of Object.entries(targets)) t[k] = Array.isArray(v) ? v : await box(v)
        frames[name] = { targets: t }
      }
      const field = (label: string) => page.locator('#panel-right div.space-y-1\\.5', { has: page.getByText(label, { exact: true }) })
      const card = (label: string) => page.locator('#panel-left [draggable=true]', { has: page.getByText(label, { exact: true }) })
      const handle = (node: string, kind: 'source' | 'target') => page.locator(`${node} .react-flow__handle.${kind}`)
      const centre = async (l: Locator) => { const [x, y, w, h] = await box(l); return { x: x + w / 2, y: y + h / 2 } }
      const connect = async (from: Locator, to: Locator) => {
        const a = await centre(from), b = await centre(to)
        await page.mouse.move(a.x, a.y); await page.mouse.down(); await page.mouse.move(b.x, b.y, { steps: 12 }); await page.mouse.up()
      }
      const addField = async (name: string) => {
        await page.locator('#panel-left').getByRole('button', { name: s.addField }).click()
        await page.locator('#panel-left input').last().fill(name)
      }
      // the output field is in the Config panel's Data tab (TASK-0121); back to Settings afterwards
      const configTab = (k: 'settings' | 'data') => page.locator(`#config-tab-${k}`).click()
      const pickOutput = async (name: string) => { await configTab('data'); await field(s.output).getByRole('combobox').click(); await page.getByRole('option', { name, exact: true }).click() }

      await page.addInitScript(([l]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', 'light') }, [lang])
      await page.goto('/login'); await expect(page.locator('#auth-submit')).toBeVisible()
      const token = await signIn(page, 'admin@example.com', 'admin123')
      const H = { Authorization: `Bearer ${token}` }
      for (const w of (await (await page.request.get('/api/workflows', { headers: H })).json()).data)
        if (w.id !== 'example') await page.request.delete(`/api/workflows/${w.id}?force=true`, { headers: H })
      // Approval channels the Human node can send to, against the e2e fake chat APIs
      for (const c of (await (await page.request.get('/api/approvals/channels', { headers: H })).json()).data.channels)
        await page.request.delete(`/api/approvals/channels/${c.id}`, { headers: H })
      const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
      for (const data of [{ kind: 'slack', bot_token: 'xoxb-1111-2222-e2etoken', signing_secret: '0123456789abcdef0123456789abcdef' },
        { kind: 'telegram', bot_token: '123456:e2e-bot-token-0123456789abcdef' }, { kind: 'teams', webhook_url: `${CHAT}/teams/hook-quickstart` }])
        expect((await page.request.post('/api/approvals/channels', { headers: H, data })).ok()).toBeTruthy()

      // 1. Create: New workflow → Blank workflow
      await page.goto('/workflows'); await expect(page.locator('#new-wf')).toBeVisible()
      await snap('list', { newWf: page.locator('#new-wf') })
      await page.locator('#new-wf').click(); await expect(page.locator('#template-gallery')).toBeVisible()
      await snap('gallery', { blank: page.locator('#tpl-blank') })
      await page.locator('#tpl-blank').click(); await expect(page.locator('.react-flow__node')).toHaveCount(2)
      const wid = page.url().split('/workflows/')[1]
      await page.getByLabel(s.wfName).fill(s.name)

      // 2. Build: drop an LLM and a Human node, wire Start → LLM → Human → End
      const pane = page.locator('.react-flow__pane')
      for (let i = 0; i < 2; i++) { await page.locator('.react-flow__controls-zoomout').click(); await page.waitForTimeout(250) }
      const [px, py] = await box(pane)
      const LLM_AT = { x: 260, y: 420 }, HUMAN_AT = { x: 560, y: 420 }
      const dropLlm: Box = [px + LLM_AT.x, py + LLM_AT.y, 1, 1], dropHuman: Box = [px + HUMAN_AT.x, py + HUMAN_AT.y, 1, 1]
      await snap('blank', { llm: card('LLM'), dropLlm })
      await card('LLM').dragTo(pane, { targetPosition: LLM_AT })
      // Human sits below the fold of the palette: scroll to it first, as a person would
      await card('Human').scrollIntoViewIfNeeded()
      await snap('llm-dropped', { human: card('Human'), dropHuman })
      await card('Human').dragTo(pane, { targetPosition: HUMAN_AT })
      await expect(page.locator('.react-flow__node')).toHaveCount(4)
      await snap('both-dropped', { edge: page.locator('[data-testid="rf__edge-e1"]') })
      await page.locator('[data-testid="rf__edge-e1"] path').first().click({ force: true }); await page.keyboard.press('Delete')
      await expect(page.locator('.react-flow__edge')).toHaveCount(0)
      const start = '.react-flow__node[data-id="start"]', end = '.react-flow__node[data-id="end"]', llm = '.react-flow__node-llm', human = '.react-flow__node-human'
      await snap('dropped', {
        startOut: handle(start, 'source'), llmIn: handle(llm, 'target'), llmOut: handle(llm, 'source'),
        humanIn: handle(human, 'target'), humanOut: handle(human, 'source'), endIn: handle(end, 'target'),
      })
      await connect(handle(start, 'source'), handle(llm, 'target'))
      await connect(handle(llm, 'source'), handle(human, 'target'))
      await connect(handle(human, 'source'), handle(end, 'target'))
      await expect(page.locator('.react-flow__edge')).toHaveCount(3)
      await pane.click({ position: { x: 30, y: 30 } }); await page.keyboard.press('Shift+L'); await page.waitForTimeout(400)
      await page.keyboard.press('Shift+1'); await page.waitForTimeout(600)
      await snap('wired', { llm: page.locator(llm) })

      // 3. Configure: prompt and output field of the LLM node, question of the Human node
      await page.locator(llm).click()
      await snap('llm-selected', { label: field(s.label).locator('input'), prompt: page.locator('#llm-prompt'), addField: page.locator('#panel-left').getByRole('button', { name: s.addField }) })
      await field(s.label).locator('input').fill(s.draft)
      await page.locator('#llm-prompt').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText(s.prompt)
      await snap('llm-prompt', { prompt: page.locator('#llm-prompt'), tabs: page.locator('#config-tabs') })
      await addField('reply'); await pickOutput('reply')
      await snap('llm-config', { tabs: page.locator('#config-tabs'), output: field(s.output), state: page.locator('#panel-left input').last(), human: page.locator(human) })
      await page.locator(human).click(); await configTab('settings')
      await field(s.label).locator('input').fill(s.approve)
      await page.locator('#human-prompt').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText(s.question)
      await addField('decision'); await pickOutput('decision'); await configTab('settings')
      // Send the request to Slack as well; the studio still shows it to the run's owner
      await page.locator('#approval-channel').scrollIntoViewIfNeeded()
      await snap('human-config', { prompt: page.locator('#human-prompt'), tabs: page.locator('#config-tabs'), channel: page.locator('#approval-channel') })
      await page.locator('#approval-channel').click(); await expect(page.getByRole('option', { name: /Slack/ })).toBeVisible()
      await snap('channels', { list: page.getByRole('listbox'), slack: page.getByRole('option', { name: /Slack/ }) })
      await page.getByRole('option', { name: /Slack/ }).click()
      await page.locator('#approval-target').fill('C0SUPPORT')
      await snap('human-slack', { channel: page.locator('#approval-channel'), target: page.locator('#approval-target'), save: page.locator('#save-btn') })
      await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
      await pane.click({ position: { x: 30, y: 30 } })
      await snap('graph', { save: page.locator('#save-btn'), input: page.locator('#run-input') })

      // 4. Run: the LLM drafts, the Human node waits, approve, read the state diff
      await page.locator('#run-tab').click()
      await page.locator('#run-input').click(); await page.keyboard.press('ControlOrMeta+a')
      await page.keyboard.insertText(JSON.stringify({ message: s.message }, null, 2))
      await snap('input', { input: page.locator('#run-input'), run: page.locator('#run-btn') })
      await page.locator('#run-btn').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
      await expect(page.locator('#human-panel')).toBeVisible()
      await snap('waiting', { panel: page.locator('#human-panel'), approve: page.locator('#human-approve'), summary: page.locator('#trace-summary') })
      await page.locator('#human-approve').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
      await snap('done', { summary: page.locator('#trace-summary'), llm: page.locator(llm) })
      await page.locator(llm).click(); await expect(page.locator('#trace-diff')).toBeVisible()
      await snap('diff', { diff: page.locator('#trace-diff'), more: page.locator('#more-btn') })

      // 5. Ship: a token for another service, then a schedule
      await page.locator('#more-btn').click(); await expect(page.locator('#api-btn')).toBeVisible()
      await snap('more', { api: page.locator('#api-btn') })
      await page.locator('#api-btn').click(); await expect(page.locator('#api-token-name')).toBeVisible()
      await page.locator('#api-token-name').fill(s.token)
      await snap('api', { name: page.locator('#api-token-name'), create: page.locator('#api-create') })
      await page.locator('#api-create').click(); await expect(page.locator('#api-token-value')).toBeVisible()
      await snap('token', { token: page.locator('#api-token-value'), curl: page.locator('#api-curl') })
      const wft = await page.locator('#api-token-value').inputValue()
      await page.keyboard.press('Escape')
      // What the other service sees: the same call the dialog shows
      const body = { input: { message: s.message } }
      const res = await page.request.post(`/api/hooks/workflows/${wid}/runs`, { headers: { Authorization: `Bearer ${wft}` }, data: body })
      const api = { path: `/api/hooks/workflows/${wid}/runs`, body, status: res.status(), response: await res.json() }

      await page.locator('#more-btn').click(); await page.locator('#schedules-btn').click(); await expect(page.locator('#schedules-dialog')).toBeVisible()
      await page.locator('#schedule-name').fill(s.schedule); await page.locator('#schedule-cron').fill('0 9 * * 1-5')
      await expect(page.locator('#schedule-preview')).toBeVisible()
      await snap('schedule', { cron: page.locator('#schedule-cron'), preview: page.locator('#schedule-preview'), create: page.locator('#schedule-create') })
      await page.locator('#schedule-create').click(); await expect(page.getByTestId('schedule-row')).toHaveCount(1)
      await snap('scheduled', { row: page.getByTestId('schedule-row') })
      await page.keyboard.press('Escape')

      // History loads with the editor: reload to list the run the API call queued
      await page.reload(); await expect(page.locator('.react-flow__node')).toHaveCount(4)
      await page.locator('#history-all').click()
      await expect(page.getByTestId('history-row')).toHaveCount(2, { timeout: 30_000 })
      await snap('history', { rows: page.getByTestId('history-row').first() })

      // 6. New: the Agent node from its template, an approved tool call, its rounds, time travel, MCP, the phone layout
      await page.goto('/workflows'); await page.locator('#new-wf').click(); await expect(page.locator('#template-gallery')).toBeVisible()
      const agentCard = page.locator('[data-testid=tpl-card][data-id=builtin-support-agent]')
      await agentCard.scrollIntoViewIfNeeded()
      await snap('gallery-agent', { card: agentCard })
      await agentCard.locator('button').first().click()
      const agent = '.react-flow__node-agent'
      await expect(page.locator(agent)).toBeVisible()
      const agentWid = page.url().split('/workflows/')[1]
      // The policy search tool needs a knowledge base: a small one, picked for it, as the user would before the first run
      for (const k of (await (await page.request.get('/api/knowledge-bases', { headers: H })).json()).data)
        if (k.name === s.kb) await page.request.delete(`/api/knowledge-bases/${k.id}`, { headers: H })
      const kb = (await (await page.request.post('/api/knowledge-bases', { headers: H, data: { name: s.kb } })).json()).data
      const awf = (await (await page.request.get(`/api/workflows/${agentWid}`, { headers: H })).json()).data
      for (const n of awf.nodes) if (n.type === 'agent') for (const tl of n.data.tools) if (tl.source === 'knowledge') tl.knowledge_base_id = kb.id
      expect((await page.request.post('/api/workflows', { headers: H, data: awf })).ok()).toBeTruthy()
      await page.reload(); await expect(page.locator(agent)).toBeVisible()
      await page.locator(agent).click(); await configTab('settings')
      await page.locator('#agent-tool-2').scrollIntoViewIfNeeded()
      await snap('agent', { node: page.locator(agent), tool: page.locator('#agent-tool-2'), approval: page.locator('#agent-tool-2-approval') })
      await page.locator('#run-tab').click()
      await page.locator('#run-input').click(); await page.keyboard.press('ControlOrMeta+a')
      await page.keyboard.insertText(JSON.stringify({ message: s.refund }, null, 2))
      await page.locator('#run-btn').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
      await snap('agent-waiting', { panel: page.locator('#human-panel'), approve: page.locator('#human-approve') })
      await page.locator('#human-approve').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
      await snap('agent-trace', { timeline: page.locator('#trace-timeline'), round: page.locator('.trace-row[data-span="agent/__model#1"]'), travel: page.locator('#trace-time-travel') })
      await page.locator('#trace-time-travel').click()
      const cps = page.getByTestId('checkpoint')
      await expect(cps.first()).toBeVisible(); await cps.first().click()
      await snap('time-travel', { list: cps.first(), state: page.locator('#checkpoint-state'), fork: page.locator('#time-travel-fork') })
      await page.keyboard.press('Escape'); await expect(page.locator('#time-travel-dialog')).toHaveCount(0)
      await page.locator('#more-btn').click(); await page.locator('#api-btn').click(); await page.locator('#api-mcp-tab').click()
      await page.locator('#mcp-enabled').click(); await expect(page.locator('#mcp-snippet')).toBeVisible()
      await snap('mcp', { enabled: page.locator('#mcp-enabled'), snippet: page.locator('#mcp-snippet') })
      await page.keyboard.press('Escape')
      // The phone layout: the same signed-in session at 390x844, saved as phone-*.png (shown in a phone frame)
      const phone = await browser.newContext({ storageState: await page.context().storageState(), viewport: { width: 390, height: 844 },
        deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: lang === 'en' ? 'en-US' : 'vi-VN' })
      const mob = await phone.newPage()
      await mob.goto(`/workflows/${agentWid}`); await expect(mob.locator('#mobile-tab-canvas')).toBeVisible(); await mob.waitForTimeout(600)
      await mob.screenshot({ path: `${dir}/phone-canvas.png` })
      await mob.locator(agent).click(); await mob.locator('#mobile-tab-config').click(); await expect(mob.locator('#config-tabs')).toBeVisible()
      await mob.waitForTimeout(450); await mob.screenshot({ path: `${dir}/phone-config.png` })
      await phone.close()

      fs.writeFileSync(`${dir}/flow.json`, JSON.stringify({ viewport: [1440, 900], frames, api }, null, 2))
      for (const [frame, doc] of Object.entries(DOC)) fs.copyFileSync(`${dir}/${frame}.png`, `../handbook/docs/${lang}/images/${doc}.png`)
    })
  })
}
