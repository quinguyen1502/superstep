import { test, expect } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
import { expectRowAligned, expectBaselineAligned } from './helpers/alignment'
// the bottom panel (Run · Test · Code; Run = input | logs, a run picker and "View all") and the Chat side
// panel (header button or Shift+C, 340–760px, width and open state remembered, fullscreen with Esc, Config beside it).
const STATE = [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }]
const WF = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: 'Reply to {{state.message}}', output_field: 'reply' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })

test('Run mode: input beside the logs, the run picker and View all', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 960 })
  const H = await login(page); const wid = await newWorkflow(page, H, WF(`Runs ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await expect(page.locator('#run-tab')).toHaveAttribute('data-state', 'active')
  await expect(page.locator('#run-input')).toBeVisible()
  for (let i = 0; i < 2; i++) { await page.locator('#run-btn').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 }) }
  await expect(page.locator('#run-input')).toBeVisible()                        // input stays beside the logs
  await expect(page.locator('#run-picker')).toContainText(/\d/)                  // the latest run is picked

  // one toolbar row: tabs, picker and View all share height and centre; time and id share a baseline
  await expectRowAligned([page.locator('#run-toolbar [role=tablist]'), page.locator('#run-picker'), page.locator('#history-all')], { label: 'run toolbar' })
  await expectBaselineAligned([page.locator('#run-picker [data-slot=run-time]'), page.locator('#run-picker [data-slot=run-id]')], { label: 'run picker' })

  await page.locator('#run-picker').click()
  await expect(page.getByRole('option')).toHaveCount(2)
  await page.getByRole('option').last().click()
  await expect(page.locator('#trace-summary')).toBeVisible()

  await page.locator('#history-all').click(); await expect(page.locator('#history-dialog')).toBeVisible()
  await expect(page.getByTestId('history-row')).toHaveCount(2)
  await page.getByTestId('history-row').first().click(); await expect(page.locator('#history-dialog')).toHaveCount(0)

  await page.locator('#tests-tab').click(); await expect(page.locator('#run-input')).toHaveCount(0)
  await page.locator('#code-tab').click(); await expect(page.locator('#code-tab')).toHaveAttribute('data-state', 'active')
  await page.locator('#run-tab').click(); await expect(page.locator('#run-input')).toBeVisible()
})

test('Chat side panel: toggle, width and open state remembered, fullscreen keeps the draft, Config beside it', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 960 })
  const H = await login(page); const wid = await newWorkflow(page, H, WF(`Chat ${Date.now()}`))
  await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true } })
  await page.goto(`/workflows/${wid}`)
  await expect(page.locator('#chat-side')).toHaveCount(0)
  await page.locator('#chat-open').click(); await expect(page.locator('#chat-side')).toBeVisible()
  await expect(page.locator('#chat-open')).toHaveAttribute('aria-pressed', 'true')
  const w0 = (await page.locator('#panel-chat').boundingBox())!.width
  expect(Math.abs(w0 - 420)).toBeLessThanOrEqual(2)

  // the chat toolbar and the editor header stay on one size each
  await expectRowAligned([page.locator('#chat-view'), page.locator('#chat-session-picker'), page.locator('#chat-new'), page.locator('#chat-fullscreen'), page.locator('#chat-close')], { label: 'chat toolbar' })
  await expectRowAligned([page.locator('#save-btn'), page.locator('#run-btn'), page.locator('#chat-open'), page.locator('#more-btn')], { label: 'editor header' })

  // Config stays beside the chat: a node can be edited while chatting
  await page.locator('.react-flow__node[data-id="bot"]').click(); await expect(page.locator('#config-panel')).toBeVisible()
  expect((await page.locator('#panel-right').boundingBox())!.width).toBeGreaterThan(200)

  // drag the chat border: 340–760px, remembered with the open state after a reload
  const h = (await page.locator('#resize-chat').boundingBox())!
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2); await page.mouse.down()
  await page.mouse.move(h.x - 600, h.y + h.height / 2, { steps: 8 }); await page.mouse.up()
  const w1 = (await page.locator('#panel-chat').boundingBox())!.width
  expect(w1).toBeGreaterThan(740); expect(w1).toBeLessThanOrEqual(762)
  await page.reload(); await expect(page.locator('#chat-side')).toBeVisible()
  expect(Math.abs((await page.locator('#panel-chat').boundingBox())!.width - w1)).toBeLessThanOrEqual(2)

  // fullscreen keeps the conversation and the draft; Esc leaves it
  await page.locator('#chat-input').fill('draft kept')
  await page.locator('#chat-fullscreen').click(); await expect(page.locator('#chat-side')).toHaveAttribute('data-fullscreen', 'true')
  await expect(page.locator('#chat-input')).toHaveValue('draft kept')
  // fullscreen: the icon-only New chat sits in the sidebar header, level with the chat toolbar
  await expect(page.locator('#chat-new')).toHaveAttribute('aria-label', 'Chat mới'); await expect(page.locator('#chat-new')).toHaveText('')
  await expectRowAligned([page.locator('#chat-new'), page.locator('#chat-fullscreen'), page.locator('#chat-close')], { label: 'fullscreen chat header' })
  await expectRowAligned([page.locator('#chat-sidebar-header > span'), page.locator('#chat-new')], { sameHeight: false, label: 'chat sidebar header' })
  await page.keyboard.press('Escape'); await expect(page.locator('#chat-side')).not.toHaveAttribute('data-fullscreen', 'true')
  await expect(page.locator('#chat-input')).toHaveValue('draft kept')

  // × closes, Shift+C (on the canvas) toggles
  await page.locator('#chat-close').click(); await expect(page.locator('#chat-side')).toHaveCount(0)
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('Shift+C'); await expect(page.locator('#chat-side')).toBeVisible()
  await page.locator('.react-flow__pane').click(); await page.keyboard.press('Shift+C'); await expect(page.locator('#chat-side')).toHaveCount(0)
  await page.reload(); await expect(page.locator('#run-btn')).toBeVisible(); await expect(page.locator('#chat-side')).toHaveCount(0)
})

test('narrow screens: Config folds away while nothing is selected', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 860 })
  const H = await login(page); const wid = await newWorkflow(page, H, WF(`Narrow ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await expect.poll(async () => (await page.locator('#panel-right').boundingBox())?.width ?? 0).toBeGreaterThan(200)
  await page.locator('#chat-open').click(); await expect(page.locator('#chat-side')).toBeVisible()   // 1280 - 420 < 1100
  await expect.poll(async () => (await page.locator('#panel-right').boundingBox())?.width ?? 0).toBeLessThan(2)
  await page.locator('.react-flow__node[data-id="bot"]').click()
  await expect.poll(async () => (await page.locator('#panel-right').boundingBox())?.width ?? 0).toBeGreaterThan(200)
  await page.locator('.react-flow__pane').click({ position: { x: 30, y: 30 } })
  await expect.poll(async () => (await page.locator('#panel-right').boundingBox())?.width ?? 0).toBeLessThan(2)
})

// The left panel at its narrowest: nothing in the palette or STATE SCHEMA list may push past the panel edge
// (the ScrollArea content used to be a `display: table` div that grew to the long vi reducer label).
for (const lang of ['en', 'vi'] as const) {
  test(`left panel content fits its width (${lang})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const H = await login(page)
    const wid = await newWorkflow(page, H, { name: 'Narrow', state: [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'meta', type: 'object' }],
      nodes: [N('s', 'start', 40), N('e', 'end', 300)], edges: [{ id: '1', source: 's', target: 'e' }] })
    await page.evaluate(l => { localStorage.setItem('lang', l); localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 180, right: 300, bottom: 260 })) }, lang)
    await page.goto(`/workflows/${wid}`); await page.locator('#palette-state-tab').click(); await expect(page.locator('#reducer-messages')).toBeVisible()
    const panel = (await page.locator('#panel-left').boundingBox())!
    for (const vp of await page.locator('#panel-left [data-slot=scroll-area-viewport]').all()) {
      const { sw, cw } = await vp.evaluate(e => ({ sw: e.scrollWidth, cw: e.clientWidth }))
      expect(sw, 'left panel scroll viewport overflows').toBeLessThanOrEqual(cw)
    }
    await page.locator('#palette-state-tab').click()
    for (const el of await page.locator('[data-testid=state-field] input, [data-testid=state-field] button, #reducer-messages, #reducer-meta').all()) {
      const b = (await el.boundingBox())!
      expect(b.x + b.width, 'control past the left panel edge').toBeLessThanOrEqual(panel.x + panel.width + 0.5)
    }
    // narrow: the name takes its own line, type + delete share the next one; all controls keep the default 32px
    const field = page.locator('[data-testid=state-field]').first()
    await expectRowAligned(await field.locator('> div > button').all(), { label: 'state field type + delete' })
    expect((await field.locator('input').boundingBox())!.width, 'name input stays usable').toBeGreaterThan(100)
    expect(Math.round((await field.locator('input').boundingBox())!.height)).toBe(32)
  })
}

// The compact chat toolbar at the 340px minimum: View as is an icon menu, so the session picker keeps a usable width.
for (const lang of ['en', 'vi'] as const) {
  test(`compact chat toolbar keeps the session picker usable (${lang})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const H = await login(page)
    const wid = await newWorkflow(page, H, { name: 'Compact', state: [{ name: 'message', type: 'string' }], nodes: [N('s', 'start', 40), N('e', 'end', 300)], edges: [{ id: '1', source: 's', target: 'e' }] })
    await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true } })
    await page.evaluate(l => { localStorage.setItem('lang', l); localStorage.setItem('lgs.chatPanel', JSON.stringify({ open: true, width: 340 })) }, lang)
    await page.goto(`/workflows/${wid}`); await expect(page.locator('#chat-session-picker')).toBeVisible()
    const tb = (await page.locator('#chat-toolbar').boundingBox())!
    expect(Math.round(tb.width)).toBeLessThanOrEqual(341)
    await expect(page.locator('#chat-session-picker [data-slot=select-value]')).toBeVisible()
    const fresh = (await page.locator('#chat-new').boundingBox())!, expand = (await page.locator('#chat-fullscreen').boundingBox())!
    expect(fresh.x + fresh.width).toBeLessThanOrEqual(expand.x)
    expect(fresh.x).toBeGreaterThan(tb.x + tb.width / 2)
    const row = await page.locator('#chat-toolbar > button:visible, #chat-toolbar > [data-slot=select-trigger]:visible').all()
    await expectRowAligned(row, { label: 'compact chat toolbar' })
    for (const r of row) { const b = (await r.boundingBox())!; expect(b.x + b.width, 'toolbar control past the panel edge').toBeLessThanOrEqual(tb.x + tb.width + 0.5) }
    await page.locator('#chat-view').click(); await expect(page.getByRole('menu')).toContainText(lang === 'vi' ? 'Xem dưới góc nhìn' : 'View as')
    await expect(page.locator('#chat-view-visitor')).toContainText(lang === 'vi' ? 'Khách chat' : 'Chat visitor')
    await expect(page.locator('#chat-view')).toHaveText(lang === 'vi' ? 'Người dựng' : 'Builder')
    // the View as label and the session title share the font size and the text baseline
    const fs = async (sel: string) => page.locator(sel).evaluate(e => getComputedStyle(e).fontSize)
    expect(await fs('#chat-view')).toBe(await fs('#chat-session-picker [data-slot=select-value]'))
    await expectBaselineAligned([page.locator('#chat-view'), page.locator('#chat-session-picker [data-slot=select-value]')], { label: 'View as label and session title' })
    for (const v of ['builder', 'visitor'] as const) {
      if (v === 'visitor') { await page.locator('#chat-view-visitor').click(); await page.locator('#chat-view').click() }
      // the View as trigger reads as a menu: its chevron sits right after the label, inside the panel
      const chevron = page.locator('#chat-view > svg'); await expect(chevron).toBeVisible()
      const label = await page.locator('#chat-view').evaluate(e => { const r = document.createRange(); r.selectNodeContents(e.firstChild!); const b = r.getBoundingClientRect(); return { right: b.right } })
      const cb = (await chevron.boundingBox())!
      expect(cb.x - label.right, `${v}: chevron right after the label`).toBeLessThanOrEqual(8)
      expect(cb.x - label.right).toBeGreaterThanOrEqual(0)
      const ob = (await page.locator('#chat-view').boundingBox())!
      expect(cb.x + cb.width, 'chevron inside its button').toBeLessThanOrEqual(ob.x + ob.width)
      await expect(page.locator('#chat-session-picker [data-slot=select-value]')).toBeVisible()
      const sw = await page.locator('#chat-toolbar').evaluate(e => e.scrollWidth - e.clientWidth); expect(sw, 'toolbar overflow').toBeLessThanOrEqual(0)
      if (v === 'visitor') { await page.keyboard.press('Escape'); await page.locator('#chat-visitor-exit').click(); await page.locator('#chat-view').click() }
    }
    await page.locator('#chat-view-visitor').click(); await expect(page.locator('#chat-view')).toHaveAttribute('aria-label', lang === 'vi' ? 'Xem dưới góc nhìn: Khách chat' : 'View as: Chat visitor')
    await expect(page.locator('#chat-view')).toHaveText(lang === 'vi' ? 'Khách' : 'Visitor')
    // the session picker's chevron hugs its title
    const val = (await page.locator('#chat-session-picker [data-slot=select-value]').boundingBox())!
    const chev = (await page.locator('#chat-session-picker > svg').boundingBox())!
    expect(chev.x - (val.x + val.width), 'chevron right after the title').toBeLessThanOrEqual(10)
    // visitor view: a banner on top of the thread, one click back to the builder view
    await expect(page.locator('#chat-visitor-banner')).toContainText(lang === 'vi' ? 'Bạn đang xem trước như khách chat' : "You're previewing what chat visitors see")
    await page.locator('#chat-visitor-exit').click()
    await expect(page.locator('#chat-visitor-banner')).toHaveCount(0); await expect(page.locator('#chat-view')).toHaveText(lang === 'vi' ? 'Người dựng' : 'Builder')
  })
}
