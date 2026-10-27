import { test, expect, type Page } from '@playwright/test'
import { apiToken, newWorkflow, N } from './helpers'
// REQ-0074 (TASK-0143): a published chat embedded on another site. The widget's bubble opens the chat in an iframe and
// the visitor keeps their chat after a reload (the token lives on the host page); a plain iframe works too; a site
// that is not in embed_origins cannot frame the page. (The studio's own pages refuse frames through nginx and the
// all-in-one image, not the Vite dev server: backend/tests/test_frame_headers.py and the smoke scripts cover them.)
const shot = async (page: Page, name: string) => { if (process.env.REVIEW_SHOTS) await page.screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const STUDIO = `http://127.0.0.1:${process.env.E2E_UI_PORT || 5190}`
const HOST = 'http://localhost:5999', OTHER = 'http://localhost:5998'
const STATE = [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }]
const ECHO = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: 'History:\n{{state.messages}}', output_field: 'reply' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
// The other site's pages are made up by the test, so Chrome counts them as public: its Local Network Access check would
// then refuse their requests to this studio on 127.0.0.1. Real hosts and studios are both public, so turn it off here.
test.use({ launchOptions: { ...(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {}),
  args: ['--disable-features=LocalNetworkAccessChecks,PrivateNetworkAccessSendPreflights,PrivateNetworkAccessRespectPreflightResults'] } })

/** A page of another site, served by the test: its body is `html`. */
const site = (page: Page, origin: string, html: string) =>
  page.route(`${origin}/**`, r => r.fulfill({ contentType: 'text/html', body: `<!doctype html><html lang="en"><body><h1>Shop</h1>${html}</body></html>` }))

async function publish(page: Page) {
  await page.goto('/login'); await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
  const H = { Authorization: `Bearer ${await apiToken(page)}` }; const n = Date.now() % 100000
  const wid = await newWorkflow(page, H, ECHO(`Shop help ${n}`)); const slug = `shop-${n}`
  const r = await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, access: 'anonymous', slug, title: 'Shop help', embed_origins: [HOST] } })
  expect((await r.json()).success).toBe(true)
  return { slug, wid }
}

test('the widget opens the chat and keeps it across a reload', async ({ page, browser }) => {
  const { slug, wid } = await publish(page)
  // the builder copies the snippets from the Chat settings
  await page.goto(`/workflows/${wid}`)
  if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
  await page.locator('#chat-view').click(); await page.locator('#chat-settings-btn').click()
  await expect(page.locator('#chat-snippet-widget-code')).toHaveValue(`<script src="${STUDIO}/c/widget.js" data-slug="${slug}" async></script>`)
  await expect(page.locator('#chat-snippet-iframe-code')).toHaveValue(new RegExp(`/c/${slug}\\?embed=1`))
  await page.locator('#chat-snippet-widget').scrollIntoViewIfNeeded()
  if (process.env.REVIEW_SHOTS) await page.locator('#chat-publish').screenshot({ path: `${process.env.REVIEW_SHOTS}/chat-embed-settings.png` })

  const host = await (await browser.newContext({ locale: 'en-US' })).newPage()
  await site(host, HOST, `<script src="${STUDIO}/c/widget.js" data-slug="${slug}" async></script>`)
  await host.goto(`${HOST}/shop.html`)
  const bubble = host.locator('#superstep-chat-button')
  await expect(bubble).toHaveAttribute('aria-label', 'Open chat'); await bubble.click()
  const chat = host.frameLocator('#superstep-chat-panel iframe')
  await expect(chat.locator('#public-chat-title')).toHaveText('Shop help')
  await chat.locator('#chat-input').fill('Where is my order?'); await chat.locator('#chat-input').press('Enter')
  await expect(chat.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  await shot(host, 'chat-embed-widget')
  expect(await host.evaluate(k => localStorage.getItem(k), `superstep-chat:${slug}`)).toMatch(/^[0-9a-f]{16}\.[0-9a-f]{32}$/)
  // a reload: the host gives the frame its token back, so the chat is still there
  await host.reload(); await host.locator('#superstep-chat-button').click()
  await expect(chat.getByTestId('chat-mine')).toHaveText(['Where is my order?'])
  await expect(chat.locator('#public-chat')).toHaveAttribute('data-embed', 'widget')
})

test('a plain iframe works; a site that is not allowed cannot frame the page', async ({ page, browser }) => {
  const { slug } = await publish(page)
  const ctx = await browser.newContext({ locale: 'vi-VN' })
  const host = await ctx.newPage()
  await site(host, HOST, `<iframe id="chat" src="${STUDIO}/c/${slug}?embed=1" style="width:420px;height:560px;border:0"></iframe>`)
  await host.goto(`${HOST}/help.html`)
  const chat = host.frameLocator('#chat')
  await chat.locator('#chat-input').fill('xin chào'); await chat.locator('#chat-input').press('Enter')
  await expect(chat.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
  await expect(chat.locator('#public-chat')).toHaveAttribute('data-embed', 'iframe')

  // a site that is not allowed is refused by frame-ancestors
  const other = await ctx.newPage()
  await site(other, OTHER, `<iframe id="chat" src="${STUDIO}/c/${slug}?embed=1"></iframe>`)
  await other.goto(`${OTHER}/x.html`); await other.waitForTimeout(1500)
  await expect(other.frameLocator('#chat').locator('#public-chat')).toHaveCount(0)
  const res = await page.request.get(`/c/${slug}`)
  expect(res.headers()['content-security-policy']).toBe(`frame-ancestors 'self' ${HOST}`)
})
