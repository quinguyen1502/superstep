import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
import { expectRowAligned, expectBaselineAligned, settled } from './helpers/alignment'

/** Alignment guardrails (docs/ui-conventions.md, rule 11): the main toolbars and rows share control heights,
 * vertical centres and text baselines, in light and dark, English and Vietnamese. */
const WF = { name: 'Align check', state: [{ name: 'message', type: 'string' }, { name: 'reply', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [N('start', 'start', 40), N('bot', 'llm', 300, { label: 'Answer', model: 'gpt-4o-mini', prompt: 'Reply to {{state.message}}', output_field: 'reply' }),
    N('ask', 'human', 560, { label: 'Approve', prompt: 'OK?', output_field: 'decision' }), N('end', 'end', 820)],
  edges: [{ id: '1', source: 'start', target: 'bot' }, { id: '2', source: 'bot', target: 'ask' }, { id: '3', source: 'ask', target: 'end' }] }

const visible = async (page: Page, sel: string) => { const l = page.locator(sel); const n = await l.count(); const out = []
  for (let i = 0; i < n; i++) if (await l.nth(i).isVisible()) out.push(l.nth(i)); return out }

for (const [lang, theme] of [['en', 'light'], ['vi', 'light'], ['en', 'dark'], ['vi', 'dark']] as const) {
  test(`rows are aligned (${theme}, ${lang})`, async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width: 1600, height: 960 })
    const H = await login(page)
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])

    // workflow list toolbar: search, credentials, import, new (same height); the show-all switch and its label (same centre)
    await page.goto('/workflows'); await expect(page.locator('#new-wf')).toBeVisible()
    const toolbar = await visible(page, '#wf-search, #creds-btn, #import-btn, #new-wf')
    await expectRowAligned(toolbar, { label: 'workflow list toolbar' })
    if (await page.locator('#wf-all').isVisible()) await expectRowAligned([page.locator('#wf-search'), page.locator('#wf-all'), page.locator('label[for=wf-all]')], { sameHeight: false, label: 'show-all switch' })
    await expectRowAligned(await visible(page, 'header :is(button, a[data-slot=button])'), { label: 'list header' })

    // dialog footers: rename (Dialog) and delete (AlertDialog)
    const wid = await newWorkflow(page, H, WF); await page.reload()
    const row = page.locator('tr', { hasText: 'Align check' }).first()
    await row.locator('.wf-actions').click(); await page.getByRole('menuitem').nth(0).click(); await expect(page.locator('#rename-input')).toBeVisible()
    await settled(page.locator('[data-slot=dialog-content]'))
    await expectRowAligned(await visible(page, '[data-slot=dialog-footer] button'), { label: 'rename dialog footer' })
    await expectBaselineAligned(await visible(page, '[data-slot=dialog-footer] button'), { label: 'rename dialog footer' })
    await page.keyboard.press('Escape'); await expect(page.locator('#rename-input')).toBeHidden()
    await row.locator('.wf-actions').click(); await page.getByRole('menuitem').nth(2).click(); await expect(page.locator('[data-slot=alert-dialog-footer]')).toBeVisible()
    await settled(page.locator('[data-slot=alert-dialog-content]'))
    await expectRowAligned(await visible(page, '[data-slot=alert-dialog-footer] button'), { label: 'delete dialog footer' })
    await page.keyboard.press('Escape')

    // editor header: every control in the top bar
    await page.goto(`/workflows/${wid}`); await expect(page.locator('#run-btn')).toBeVisible()
    // STATE SCHEMA field row at the default panel width: name, type and delete on one line, one height
    await expectRowAligned(await page.locator('[data-testid=state-field]').first().locator('> div > *').all(), { label: 'state field row' })
    await expectRowAligned(await visible(page, 'header :is(button, input, a[data-slot=button])'), { label: 'editor header' })
    await expectBaselineAligned([page.locator('#save-btn'), page.locator('#run-btn'), page.locator('#step-btn')], { label: 'editor header buttons' })

    // run panel: tab row, then the trace summary row after a run
    await expectRowAligned(await visible(page, '[role=tablist] >> nth=0 >> [role=tab]'), { label: 'run panel tabs' })
    await page.locator('#run-input').fill('{"message": "hi"}')
    await page.locator('#run-btn').click(); await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', /ok|waiting/, { timeout: 30_000 })
    await page.locator('#run-btn').hover(); await page.mouse.move(0, 0)
    const summary = await visible(page, '#trace-summary > span')
    await expectRowAligned(summary, { sameHeight: false, label: 'trace summary' })
    await expectBaselineAligned(summary, { label: 'trace summary' })
    await expectRowAligned([summary[0], ...await visible(page, '#trace-summary :is(button, [role=switch])')], { sameHeight: false, tolerance: 1, label: 'trace summary controls' })

    // config panel: the LLM model field (input + load button) and the Human deadline switch row
    await page.locator('.react-flow__node[data-id="bot"]').click()
    const load = page.locator('[id$="-load"]').first(); await expect(load).toBeVisible()
    const inputId = (await load.getAttribute('id'))!.replace(/-load$/, '')
    await expectRowAligned([page.locator(`[id="${inputId}"]`), load], { label: 'model field' })
    await page.locator('.react-flow__node[data-id="ask"]').click(); await expect(page.locator('#deadline-on')).toBeVisible()
    await expectRowAligned([page.locator('label[for=deadline-on]'), page.locator('#deadline-on')], { sameHeight: false, label: 'deadline switch row' })
    await page.locator('#deadline-on').click()
    await expectRowAligned(await visible(page, '#deadline-after, #deadline-after-unit'), { label: 'deadline duration field' })
  })
}

// The left panel at its narrowest: nothing in the palette or STATE SCHEMA list may push past the panel edge
// (the ScrollArea content used to be a `display: table` div that grew to the long vi reducer label).
for (const lang of ['en', 'vi'] as const) {
  test(`left panel content fits its width (${lang})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const H = await login(page)
    const wid = await newWorkflow(page, H, { name: 'Narrow', state: [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'meta', type: 'object' }],
      nodes: [N('s', 'start', 40), N('e', 'end', 300)], edges: [{ id: '1', source: 's', target: 'e' }] })
    await page.evaluate(l => { localStorage.setItem('lang', l); localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 180, right: 300, bottom: 260 })) }, lang)
    await page.goto(`/workflows/${wid}`); await expect(page.locator('#reducer-messages')).toBeVisible()
    const panel = (await page.locator('#panel-left').boundingBox())!
    for (const vp of await page.locator('#panel-left [data-slot=scroll-area-viewport]').all()) {
      const { sw, cw } = await vp.evaluate(e => ({ sw: e.scrollWidth, cw: e.clientWidth }))
      expect(sw, 'left panel scroll viewport overflows').toBeLessThanOrEqual(cw)
    }
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

// The editor top bar at 1440px with the chat panel open, for an admin and a viewer (view-only badge): nothing overflows,
// nothing overlaps, the controls share one row; the info badges hide whole instead of showing clipped.
for (const lang of ['en', 'vi'] as const) {
  test(`editor top bar fits at 1440px (${lang})`, async ({ page, browser }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const H = await login(page)
    const wid = await newWorkflow(page, H, { name: 'Customer support assistant', state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
      nodes: [N('s', 'start', 40), N('e', 'end', 300)], edges: [{ id: '1', source: 's', target: 'e' }] })
    const email = `bar${lang}${Date.now()}@example.com`
    expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
    expect((await page.request.put(`/api/workflows/${wid}/shares`, { headers: H, data: { email, role: 'viewer' } })).ok()).toBeTruthy()
    const check = async (p: typeof page, who: string) => {
      await p.evaluate(l => { localStorage.setItem('lang', l); localStorage.setItem('lgs.chatPanel', JSON.stringify({ open: true, width: 420 })) }, lang)
      await p.goto(`/workflows/${wid}`); await expect(p.locator('#run-btn')).toBeVisible(); await p.waitForTimeout(300)
      const r = await p.locator('header').first().evaluate(h => {
        const hb = h.getBoundingClientRect()
        const els = [...h.querySelectorAll('button, input, a, [data-slot=badge]')].filter(e => (e as HTMLElement).offsetParent && !e.closest('[data-slot=badge] *'))
        const boxes = els.map(e => ({ id: e.id || e.getAttribute('aria-label') || e.textContent || '', b: e.getBoundingClientRect() }))
        const clip = (e: Element) => { for (let x = e.parentElement; x && x !== h; x = x.parentElement) { const c = x.getBoundingClientRect(), b = e.getBoundingClientRect()
          if (getComputedStyle(x).overflow !== 'visible' && (b.left < c.left - 0.5 || b.right > c.right + 0.5)) return true } return false }
        const overlaps: string[] = []
        for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) { const a = boxes[i].b, b = boxes[j].b
          if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom && b.top < a.bottom) overlaps.push(`${boxes[i].id} / ${boxes[j].id}`) }
        return { sw: h.scrollWidth - h.clientWidth, out: boxes.filter(x => x.b.left < hb.left || x.b.right > hb.right).map(x => x.id),
          clipped: els.filter(clip).map(e => e.id || e.textContent), overlaps }
      })
      expect(r.sw, `${who}: header overflow`).toBeLessThanOrEqual(0)
      expect(r.out, `${who}: controls outside the header`).toEqual([])
      expect(r.clipped, `${who}: half-clipped controls`).toEqual([])
      expect(r.overlaps, `${who}: overlapping controls`).toEqual([])
      const row = await p.locator('#save-btn, #run-btn, #step-btn, #run-to-btn, #chat-open, #more-btn').all()
      await expectRowAligned(row, { label: `${who} top bar` })
    }
    await check(page, 'admin')
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } }); const other = await ctx.newPage(); await login(other, email, 'secret12')
    await expect(async () => { await check(other, 'viewer'); await expect(other.locator('#view-only')).toBeVisible() }).toPass({ timeout: 20_000 })
    await ctx.close()
  })
}
