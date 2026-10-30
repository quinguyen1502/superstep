import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// REQ-0078 (TASK-0184): the Help desk template. In the studio Chat tab Triage hands a duplicate charge to Billing; on the
// public page the second message of the session stays with Billing, and a new session starts at Triage again.
const BILLING = 'Billing: duplicate charges on my invoices'
const steps = (p: Page) => p.getByTestId('chat-steps').last()

async function ask(p: Page, text: string, n: number) {
  await p.locator('#chat-input').fill(text); await p.keyboard.press('Enter')
  await expect(p.getByTestId('chat-answer')).toHaveCount(n, { timeout: 20_000 })
  await expect(p.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
}

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })

  test(`the Help desk keeps the chat with the agent that answered (${lang})`, async ({ page, browser }) => {
    await page.goto('/login'); await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
    await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }; const n = Date.now() % 100000
    const wid = (await (await page.request.post('/api/templates/builtin-help-desk/use', { headers: H, data: { name: `Help desk ${lang} ${n}` } })).json()).data.id
    const slug = `desk-${lang}-${n}`
    const put = await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, access: 'anonymous', slug, steps: 'full',
      input_field: 'message', reply_field: 'answer', messages_field: 'messages' } })
    expect(put.ok()).toBeTruthy()

    // the studio Chat tab: the hand-off shows in the steps
    await page.goto(`/workflows/${wid}`)
    await expect(page.locator('.react-flow__edge.handoff-edge')).toHaveCount(3)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await ask(page, BILLING, 1)
    await expect(page.getByTestId('chat-step-handoff').first()).toContainText('Billing')

    // the public page: the second message starts at Billing
    const ctx = await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' }); const v = await ctx.newPage()
    await v.goto(`/c/${slug}`)
    await ask(v, BILLING, 1)
    await expect(steps(v)).toContainText('Triage')
    await ask(v, lang === 'vi' ? 'Khi nào tôi nhận lại tiền?' : 'When do I get the money back?', 2)
    await expect(steps(v)).toContainText('Billing'); await expect(steps(v)).not.toContainText('Triage')
    // a new session starts at Triage
    const fresh = await browser.newContext(); const f = await fresh.newPage(); await f.goto(`/c/${slug}`)
    await ask(f, 'Where is my order B200?', 1)
    await expect(steps(f)).toContainText('Triage'); await expect(steps(f)).not.toContainText('Billing')
    await ctx.close(); await fresh.close()
  })
})
