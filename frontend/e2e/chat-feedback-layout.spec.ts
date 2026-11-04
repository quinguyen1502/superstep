import { test, expect, type Locator, type Page } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { login, newWorkflow, N } from './helpers'
import { expectRowAligned } from './helpers/alignment'

const actions = '[data-testid="chat-copy"], [data-testid="chat-rate-up"], [data-testid="chat-rate-down"], [data-testid="chat-save-test"], [data-testid="chat-regenerate"]'
const comment = `Mobile feedback ${'x'.repeat(320)}`

async function aligned(answer: Locator) {
  await expect(answer.getByTestId('chat-regenerate')).toBeVisible()
  const buttons = answer.locator(actions)
  const boxes = await expectRowAligned(await buttons.all(), { label: 'answer actions' })
  expect(boxes.length).toBeGreaterThanOrEqual(4)
  const positions = await buttons.evaluateAll(elements => elements.map(el => el.getBoundingClientRect().left))
  expect(positions).toEqual([...positions].sort((a, b) => a - b))
  const footer = answer.locator('[data-slot="message-footer"]')
  expect(await footer.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
}

async function resize(page: Page, width: number, studio: boolean) {
  await page.setViewportSize({ width, height: 844 })
  if (!studio) return
  const tab = page.locator('#mobile-tab-chat')
  if (width < 768) { await expect(tab).toBeVisible(); await tab.click() }
  else await expect(tab).toHaveCount(0)
}

async function feedback(page: Page, surface: string, locale: string, theme: string, studio: boolean) {
  const answer = page.getByTestId('chat-answer').last()
  await expect(answer).toHaveAttribute('data-status', 'ok')
  await expect(answer.getByTestId('chat-regenerate')).toBeVisible()
  await aligned(answer)
  await answer.getByTestId('chat-rate-down').click()
  const input = answer.getByTestId('chat-rating-input'), send = answer.getByTestId('chat-rating-send')
  await expect(input).toBeVisible()
  if (studio) await expect(answer.getByTestId('chat-save-test')).toBeVisible()
  for (const width of [390, 320, 1280]) {
    await resize(page, width, studio)
    await aligned(answer)
    // Studio remounts its panel across desktop/mobile breakpoints; open a fresh
    // editor there rather than asserting persistence of an unsent draft.
    if (!await input.isVisible()) {
      await answer.getByTestId('chat-rate-up').click()
      await expect(answer.getByTestId('chat-rate-up')).toHaveAttribute('aria-pressed', 'true')
      await answer.getByTestId('chat-rate-down').click()
      await expect(input).toBeVisible()
    }
    await aligned(answer)
    await expectRowAligned([input, send], { label: 'feedback input and submit' })
    const footer = await answer.locator('[data-slot="message-footer"]').boundingBox()
    const field = await input.boundingBox(), submit = await send.boundingBox()
    expect(field!.x).toBeGreaterThanOrEqual(footer!.x - 1)
    expect(submit!.x + submit!.width).toBeLessThanOrEqual(footer!.x + footer!.width + 1)
    // The virtualised item contains paint: the entire 3px focus ring must fit inside it.
    const item = await input.locator('xpath=ancestor::*[@data-slot="message-scroller-item"]').boundingBox()
    expect(field!.x - item!.x).toBeGreaterThanOrEqual(3)
    expect(item!.y + item!.height - field!.y - field!.height).toBeGreaterThanOrEqual(3)
    await input.focus(); await page.keyboard.press('Shift+Tab')
    await expect(answer.getByTestId('chat-regenerate')).toBeFocused()
    await page.keyboard.press('Tab'); await expect(input).toBeFocused()
    await page.keyboard.press('Tab'); await expect(send).toBeFocused()
    if (width === 390 && process.env.REVIEW_SHOTS) {
      await input.focus()
      await page.screenshot({ path: `${process.env.REVIEW_SHOTS}/${surface}-feedback-${locale}-${theme}-${width}.png`, animations: 'disabled' })
    }
    await input.fill(comment)
    await aligned(answer)
    expect(await answer.locator('[data-slot="message-footer"]').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
  }
  await send.click()
  await expect(input).toHaveCount(0)
  await expect(answer.getByTestId('chat-rating-comment')).toHaveText(comment)
  await resize(page, 320, studio)
  await aligned(answer)
  const saved = answer.getByTestId('chat-rating-comment')
  expect(await saved.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
  await page.reload()
  if (studio) await resize(page, 320, true)
  await expect(page.getByTestId('chat-rating-comment')).toHaveText(comment)
  await aligned(page.getByTestId('chat-answer').last())
}

for (const locale of ['en', 'vi']) for (const theme of ['light', 'dark']) {
  test(`feedback actions stay on one row with mobile comments (${locale}, ${theme})`, async ({ page, browser }) => {
    const headers = await login(page), slug = `feedback-${randomUUID()}`
    const wid = await newWorkflow(page, headers, { name: `Feedback ${locale} ${theme}`,
      state: [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }],
      nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Reply', model: 'gpt-4o-mini', prompt: 'Answer {{state.message}}', output_field: 'reply' }), N('e', 'end', 560)],
      edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
    expect((await page.request.put(`/api/workflows/${wid}/chat`, { headers, data: { enabled: true, access: 'anonymous', slug } })).ok()).toBe(true)
    await page.evaluate(([lang, scheme]) => { localStorage.setItem('lang', lang); localStorage.setItem('theme', scheme) }, [locale, theme])
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`/workflows/${wid}`)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await page.locator('#chat-input').fill('Hi'); await page.locator('#chat-input').press('Enter')
    await feedback(page, 'studio', locale, theme, true)

    const context = await browser.newContext({ locale: locale === 'vi' ? 'vi-VN' : 'en-US', colorScheme: theme as 'light' | 'dark', viewport: { width: 390, height: 844 } })
    try {
      await context.addInitScript(([lang, scheme]) => { localStorage.setItem('lang', lang); localStorage.setItem('theme', scheme) }, [locale, theme])
      const visitor = await context.newPage(); await visitor.goto(`/c/${slug}`)
      await visitor.locator('#chat-input').fill('Hi'); await visitor.locator('#chat-input').press('Enter')
      await feedback(visitor, 'public', locale, theme, false)
    } finally { await context.close() }

    // The stats count this workflow's two rated sessions, rather than just the selected conversation.
    const totals = (await (await page.request.get(`/api/workflows/${wid}/chat/ratings`, { headers })).json()).data
    expect(totals.d7).toEqual({ up: 0, down: 2 }); expect(totals.d30).toEqual({ up: 0, down: 2 })
    await page.reload(); await page.locator('#mobile-tab-chat').click()
    await expect(page.locator('#chat-rating-totals')).toHaveCount(0)
    await page.locator('#more-btn').click(); await page.locator('#chat-history-btn').click()
    await expect(page.locator('#chat-history-dialog')).toBeVisible()
    await expect(page.locator('#chat-rating-totals')).toBeVisible()
    await expect(page.locator('#chat-history-dialog').getByTestId('chat-rate-down')).toHaveCount(0)
    const read = page.locator('#chat-history-dialog').getByTestId('chat-answer').last()
    await expect(read.getByTestId('chat-rating-comment')).toHaveText(comment)
    await expectRowAligned([read.getByTestId('chat-copy'), read.getByTestId('chat-save-test')], { label: 'read-only answer actions' })
    expect(await read.locator('[data-slot="message-footer"]').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
  })
}
