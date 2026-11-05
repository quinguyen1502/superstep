import { test, expect } from '@playwright/test'
import { login, newWorkflow, N, SIMPLE } from './helpers'
import { settled } from './helpers/alignment'

for (const [lang, theme] of [['en', 'light'], ['vi', 'dark']] as const) {
  test(`editor quick actions and fixed dialog body (${lang}, ${theme})`, async ({ page }) => {
    const H = await login(page)
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    const wid = await newWorkflow(page, H, SIMPLE(`Follow-ups ${lang}`))
    await page.goto(`/workflows/${wid}`)
    await page.locator('#run-picker').click()
    await expect(page.locator('[data-slot=select-empty]')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('[data-slot=select-content]')).toHaveCount(0)
    await page.locator('.react-flow__node[data-id=reply]').click()
    await expect(page.locator('#config-pane-general')).toContainText('start')
    await expect(page.locator('#config-pane-general')).toContainText('end')
    const selectedTab = page.locator('#config-tab-general')
    await selectedTab.focus()
    await selectedTab.press('ArrowRight')
    await expect(page.locator('#config-tab-settings')).toBeFocused()
    await page.locator('#config-tab-settings').press('ArrowLeft')
    await expect(selectedTab).toBeFocused()
    await settled(selectedTab)
    const appearance = await selectedTab.evaluate(el => {
      const style = getComputedStyle(el)
      // Tailwind keeps zero/transparent ring layers in the computed box-shadow.
      // Check visible paint, not one particular CSS serialization.
      const layers = style.boxShadow.match(/(?:rgba?\([^)]*\)|[^,])+/g) || []
      const visibleShadow = layers.some(layer => {
        const transparent = /rgba\([^)]*,\s*0(?:\.0+)?\s*\)/.test(layer) || /\/\s*0(?:\.0+)?\s*\)/.test(layer)
        const lengths = layer.replace(/[a-z]+\([^)]*\)/gi, '').match(/-?(?:\d*\.)?\d+px/g) || []
        return layer.trim() !== 'none' && !transparent && lengths.some(length => Math.abs(parseFloat(length)) > 0.01)
      })
      return { visibleShadow, outline: style.outlineStyle, outlineWidth: parseFloat(style.outlineWidth) }
    })
    expect(appearance.visibleShadow).toBe(false)
    expect(appearance.outline).not.toBe('none')
    expect(appearance.outlineWidth).toBeGreaterThan(0)
    await page.locator('#config-tab-data').click()
    const add = lang === 'en' ? 'Add state field' : 'Thêm trường state'
    await page.getByRole('button', { name: add, exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    const name = dialog.locator('input').first()
    await name.fill('answer')
    await expect(dialog.getByRole('alert')).toBeVisible()
    await name.fill('summary')
    await dialog.getByRole('button', { name: lang === 'en' ? 'Add field' : 'Thêm trường', exact: true }).click()
    await expect(page.locator('#config-pane-data').getByRole('combobox').first()).toContainText('summary')
    await page.locator('#undo-btn').click()
    await expect(page.locator('#config-pane-data').getByRole('combobox').first()).toContainText('answer')
    await page.locator('#more-btn').click(); await page.locator('#chat-settings-menu').click()
    await page.locator('#chat-enabled').waitFor()
    await page.setViewportSize({ width: 390, height: 640 })
    const shell = page.locator('#chat-settings')
    await settled(shell)
    const before = await shell.locator('[data-slot=dialog-header]').boundingBox()
    const footer = await shell.locator('[data-slot=dialog-footer]').boundingBox()
    await shell.locator('[data-slot=dialog-body]').evaluate(el => { el.scrollTop = el.scrollHeight })
    const after = await shell.locator('[data-slot=dialog-header]').boundingBox()
    expect(after?.y).toBe(before?.y)
    expect((await shell.locator('[data-slot=dialog-footer]').boundingBox())?.y).toBe(footer?.y)
    await expect(page.locator('#chat-settings-save')).toBeInViewport()
  })
}

test('public chat appears and completes in an already-open Studio log', async ({ page, browser }) => {
  const H = await login(page)
  const workflow = SIMPLE('Public live history')
  workflow.nodes.splice(1, 0,
    N('slow1', 'tool', 150, { label: 'Slow step 1', mode: 'function', function: 'sleep_demo', output_field: 'answer' }),
    N('slow2', 'tool', 220, { label: 'Slow step 2', mode: 'function', function: 'sleep_demo', output_field: 'answer' }))
  workflow.nodes.forEach((node, index) => { node.position.x = 40 + index * 230 })
  workflow.edges = [{ id: 's1', source: 'start', target: 'slow1' }, { id: 's2', source: 'slow1', target: 'slow2' },
    { id: 's3', source: 'slow2', target: 'reply' }, { id: 's4', source: 'reply', target: 'end' }]
  const wid = await newWorkflow(page, H, workflow)
  const settings = (await (await page.request.put(`/api/workflows/${wid}/chat`, { headers: H,
    data: { enabled: true, access: 'anonymous', input_field: 'message', reply_field: 'answer', steps: 'full' } })).json()).data
  await page.goto(`/workflows/${wid}`)
  let navigations = 0
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++ })
  await page.locator('#history-all').click()
  const guestContext = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'vi-VN' })
  try {
    const guest = await guestContext.newPage()
    await guest.goto(`/c/${settings.slug}`)
    await guest.locator('#chat-input').fill('A public message for the live log'); await guest.locator('#chat-input').press('Enter')
    await page.bringToFront()
    await expect(page.getByTestId('history-row')).toHaveCount(1, { timeout: 30000 })
    await expect(page.getByTestId('history-row')).toContainText('A public message')
    await expect(page.getByTestId('history-row').locator('[data-slot=badge]').first()).toContainText('đang chạy')
    await expect(page.getByTestId('history-duration')).not.toContainText('-')
    await expect(page.getByTestId('history-duration')).toHaveText(/\d/)
    await page.getByTestId('history-row').click()
    await expect(page.locator('#history-dialog')).toHaveCount(0)
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'running')
    await page.screenshot({ path: test.info().outputPath('public-run-running.png') })
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30000 })
    await page.screenshot({ path: test.info().outputPath('public-run-completed.png') })
    await expect(page.locator('#run-picker')).not.toContainText('Chọn run')
    expect(navigations).toBe(0)
  } finally { await guestContext.close() }
})
