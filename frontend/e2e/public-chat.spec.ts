import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { apiToken, newWorkflow, N } from './helpers'
const LOGO = path.resolve(import.meta.dirname, '../public/apple-touch-icon.png')
// REQ-0074 (TASK-0142): the published chat page /c/{slug}. The builder publishes it in Chat settings; an anonymous browser
// chats there and comes back to its chat; another browser sees none of it; the builder reads it under Visitors.
// signed_in sends a visitor to the login page; a chat that is turned off, and the daily cap, say so on the page.
// The logo (TASK-0145) shows in the header, over the welcome and in the tab; a chat without one shows its initial and a picture.
const shot = async (page: Page, name: string, sel = 'body') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const STATE = [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }]
const ECHO = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: 'History:\n{{state.messages}}', output_field: 'reply' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
const T = {
  vi: { gone: 'Chat không mở', visitors: 'Khách', daily: 'Chat này đã hết lượt tin nhắn hôm nay' },
  en: { gone: 'Chat not available', visitors: 'Visitors', daily: 'This chat has used its messages for today' },
}

/** Signs in on the login page (any UI language) and lands where `next` says. */
async function signIn(page: Page, landing = /\/workflows$/) {
  await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(landing)
}
async function login(page: Page) {
  await page.goto('/login'); await signIn(page)
  return { Authorization: `Bearer ${await apiToken(page)}` }
}

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })

  test(`publish a chat, a visitor chats on the page (${lang})`, async ({ page, browser }) => {
    const H = await login(page); const n = Date.now() % 100000
    const wid = await newWorkflow(page, H, ECHO(`Help desk ${lang} ${n}`)); const slug = `help-${lang}-${n}`
    // the builder publishes it from the Chat settings
    await page.goto(`/workflows/${wid}${lang === 'en' ? '?theme=dark' : ''}`)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await page.locator('#chat-turn-on').click()
    await page.locator('#chat-enabled').click()
    await page.locator('#chat-access').click(); await page.getByRole('option').nth(1).click()   // anyone with the link
    await page.locator('#chat-slug').fill(slug)
    await page.locator('#chat-title').fill('Order help')
    await page.locator('#chat-intro').fill('Ask about **your order**.')
    await page.locator('#chat-add-suggestion').click(); await page.locator('#chat-suggestion-0').fill('Where is my order?')
    await page.locator('#chat-logo-file').setInputFiles(LOGO)
    await expect(page.locator('#chat-logo-preview img')).toBeVisible(); await expect(page.locator('#chat-logo-remove')).toBeVisible()
    await shot(page, `public-chat-settings-${lang}`, '#chat-settings')
    await page.locator('#chat-settings-save').click(); await expect(page.locator('#chat-settings')).toHaveCount(0)

    // an anonymous browser: the intro, a suggested message, the answer, and the chat is there after a reload
    const ctx = await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', colorScheme: lang === 'en' ? 'dark' : 'light' })
    const v = await ctx.newPage()
    await v.goto(`/c/${slug}`)
    await expect(v.locator('#public-chat-title')).toHaveText('Order help')
    await expect(v.locator('#public-chat-intro')).toContainText('your order')
    await expect(v.locator('#public-chat-logo img')).toBeVisible(); await expect(v.locator('#public-chat-hero img')).toBeVisible()
    await expect(v.locator('#public-chat-illustration')).toHaveCount(0)
    await expect(v.locator('#public-chat-favicon')).toHaveAttribute('href', /\/api\/public\/chat\/.+\/logo\?v=[0-9a-f]{16}$/)
    await shot(v, `public-chat-empty-${lang}`)
    await v.getByTestId('chat-suggestion').click()
    await expect(v.getByTestId('chat-mine').last()).toHaveText('Where is my order?')
    await expect(v.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await v.locator('#chat-input').fill('And the refund?'); await v.keyboard.press('Enter')
    await expect(v.getByTestId('chat-answer')).toHaveCount(2, { timeout: 20_000 }); await expect(v.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await expect(v.getByTestId('chat-answer').last()).toContainText('Where is my order?')   // the history went to the workflow
    await shot(v, `public-chat-answer-${lang}`)
    await v.reload(); await expect(v.getByTestId('chat-mine')).toHaveCount(2)
    await expect(v.locator('#public-chat-sessions')).toBeVisible()
    await v.setViewportSize({ width: 390, height: 760 }); await shot(v, `public-chat-phone-${lang}`)

    // another browser sees none of it
    const other = await (await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })).newPage()
    await other.goto(`/c/${slug}`); await expect(other.locator('#public-chat-intro')).toBeVisible()
    await expect(other.locator('#public-chat-sessions')).toHaveCount(0); await expect(other.getByTestId('chat-mine')).toHaveCount(0)

    // the builder reads it under Visitors, read-only
    await page.reload()
    await page.locator('#chat-session-picker').click()
    await page.getByTestId('chat-visitor-option').first().click()
    await expect(page.locator('#chat-visitor-readonly')).toBeVisible()
    await expect(page.getByTestId('chat-mine')).toHaveCount(2); await expect(page.locator('#chat-input')).toHaveCount(0)
    await shot(page, `public-chat-visitors-${lang}`, '#chat-panel')
    await ctx.close()
  })

  test(`signed-in chats, a chat turned off, and the daily cap (${lang})`, async ({ page, browser }) => {
    const H = await login(page); const n = Date.now() % 100000
    const wid = await newWorkflow(page, H, ECHO(`Members ${lang} ${n}`)); const slug = `members-${lang}-${n}`
    const put = (data: Record<string, unknown>) => page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data })
    expect((await (await put({ enabled: true, access: 'signed_in', slug })).json()).success).toBe(true)
    const v = await (await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })).newPage()
    await v.goto(`/c/${slug}`)
    await expect(v).toHaveURL(new RegExp(`/login\\?next=${encodeURIComponent(`/c/${slug}`)}`))
    // signed in, the visitor comes back to the chat
    await signIn(v, new RegExp(`/c/${slug}$`))
    await expect(v.locator('#public-chat-intro')).toBeVisible()
    // no logo: the title's first letter and the picture
    await expect(v.locator('#public-chat-logo')).toHaveText('M'); await expect(v.locator('#public-chat-illustration')).toBeVisible()
    await expect(v.locator('#public-chat-favicon')).toHaveCount(0)
    await shot(v, `public-chat-default-${lang}`)

    // the daily cap: one message, then the page says so
    await put({ access: 'anonymous', daily_limit: 1 })
    const a = await (await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })).newPage()
    await a.goto(`/c/${slug}`)
    await a.locator('#chat-input').fill('one'); await a.keyboard.press('Enter')
    await expect(a.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await a.locator('#chat-input').fill('two'); await a.keyboard.press('Enter')
    await expect(a.locator('#public-chat-error')).toContainText(T[lang].daily)

    // turned off: the page says the chat is not available
    await put({ enabled: false })
    await a.reload(); await expect(a.locator('#public-chat-gone')).toContainText(T[lang].gone)
    await shot(a, `public-chat-gone-${lang}`)
  })
})
