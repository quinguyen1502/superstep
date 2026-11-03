import { createHmac } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
const STUDIO = `http://127.0.0.1:${process.env.E2E_UI_PORT || 5190}`, HOST = 'http://localhost:5999', OTHER = 'http://localhost:5998'
const LOGO = 'data:image/png;base64,' + fs.readFileSync(path.resolve(import.meta.dirname, '../public/icon-192.png')).toString('base64')
test.use({ trace: 'off', screenshot: 'off', launchOptions: {
  ...(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {}),
  args: ['--disable-features=LocalNetworkAccessChecks,PrivateNetworkAccessSendPreflights,PrivateNetworkAccessRespectPreflightResults'],
} })
async function fixture(page: Page, origins = [STUDIO]) {
  const headers = await login(page), slug = `widget-${Date.now()}`
  const wid = await newWorkflow(page, headers, SIMPLE('Widget API'))
  expect((await page.request.put(`/api/workflows/${wid}/chat`, { headers, data: { enabled: true, slug, title: 'Superstep assistant', access: ['anonymous', 'app'], reply_field: 'answer', embed_origins: [HOST] } })).ok()).toBe(true)
  const key = (await (await page.request.post(`/api/workflows/${wid}/chat/app-keys`, { headers, data: { label: 'Host server', origins } })).json()).data
  const mint = (sub: string, expired = false) => {
    const now = Math.floor(Date.now() / 1000), part = (v: unknown) => Buffer.from(JSON.stringify(v)).toString('base64url')
    const unsigned = `${part({ alg: 'HS256', typ: 'JWT', kid: key.key_id })}.${part({ iss: key.key_id, aud: `superstep-chat:${slug}`, sub, iat: now - 180, exp: expired ? now - 120 : now + 600 })}`
    return `${unsigned}.${createHmac('sha256', key.secret).update(unsigned).digest('base64url')}`
  }
  return { slug, mint }
}
const api = async (page: Page, method: 'identify' | 'logout', sub = 'lan') => page.evaluate(async ({ method, sub }) => {
  const widget = window.Superstep as import('../src/widget/protocol').WidgetAPI
  if (method === 'logout') await widget.logout()
  else await widget.identify(async () => (await (await fetch(`/token?sub=${encodeURIComponent(sub)}`)).json()).token)
}, { method, sub })
const send = async (chat: ReturnType<Page['frameLocator']>, text: string) => {
  await chat.locator('#chat-input').fill(text); await chat.locator('#chat-input').press('Enter')
  await expect(chat.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20000 })
}
test('queued widget API isolates users, refreshes tokens, restores anonymous history and emits safe events across origins', async ({ page, browser }) => {
  const { slug, mint } = await fixture(page)
  const context = await browser.newContext({ locale: 'en-US', viewport: { width: 1100, height: 850 } }), host = await context.newPage()
  let calls = 0, expiredRejections = 0, allowFresh = false
  host.on('response', async response => {
    if (response.url().startsWith(`${STUDIO}/api/public/v1/chat/`) && response.status() === 401) {
      allowFresh = true
      if ((await response.json()).error?.code === 'CHAT_TOKEN_EXPIRED') expiredRejections++
    }
  })
  await host.route(`${HOST}/**`, async route => {
    const url = new URL(route.request().url())
    if (url.pathname === '/token') { calls++; return route.fulfill({ json: { token: mint(url.searchParams.get('sub') || 'lan', calls > 1 && !allowFresh) } }) }
    await route.fulfill({ contentType: 'text/html', body: `<!doctype html><html lang="en"><head><title>Widget host</title></head><body><main><h1>Customer portal</h1><p>Ask our assistant for help.</p></main>
      <script>window.events=[];window.channel='';addEventListener('message', e=>{if(e.origin===${JSON.stringify(STUDIO)}&&e.data.type==='superstep-chat:ready')window.channel=e.data.channel});
      window.Superstep={q:[['init',{slug:${JSON.stringify(slug)},open:true}],...['ready','open','close','message','answer','error'].map(name=>['on',name,data=>window.events.push({name,data})])]};</script>
      <script src="${STUDIO}/c/widget.js" async></script></body></html>` })
  })
  await host.goto(`${HOST}/portal`)
  const chat = host.frameLocator('#superstep-chat-panel iframe')
  await expect(chat.locator('#public-chat-title')).toHaveText('Superstep assistant')
  await send(chat, 'Anonymous order')
  await expect.poll(() => host.evaluate(() => (window as any).events.filter((e: any) => e.name === 'answer').length)).toBe(1)
  if (process.env.REVIEW_SHOTS) await host.screenshot({ animations: 'disabled', path: `${process.env.REVIEW_SHOTS}/widget-en.png` })
  const guest = await host.evaluate(key => localStorage.getItem(key), `superstep-chat:${slug}`)
  expect(guest).toMatch(/^[0-9a-f]{16}\.[0-9a-f]{32}$/)
  await api(host, 'identify')
  await expect.poll(() => expiredRejections).toBeGreaterThanOrEqual(1)
  await expect(chat.getByTestId('chat-mine')).toHaveCount(0)
  await send(chat, 'Lan private order')
  expect(calls).toBeGreaterThanOrEqual(4) // an expired REST credential retried through the host's provider
  await api(host, 'identify', 'minh'); await expect(chat.getByTestId('chat-mine')).toHaveCount(0)
  await send(chat, 'Minh private order')
  await api(host, 'identify', 'lan'); await expect(chat.getByTestId('chat-mine')).toHaveText(['Lan private order'])
  // A real other-origin window obtains only the public handshake nonce, then attempts to change the identity.
  const channel = await host.evaluate(() => (window as any).channel)
  await host.route(`${OTHER}/**`, route => route.fulfill({ contentType: 'text/html', body: `<script>parent.frames[0].postMessage({type:'superstep-chat:identity',v:1,channel:${JSON.stringify(channel)},epoch:999,visitor:'new'},${JSON.stringify(STUDIO)})</script>` }))
  await host.evaluate(origin => { const attacker = document.createElement('iframe'); attacker.id = 'foreign'; attacker.src = `${origin}/attack`; document.body.append(attacker) }, OTHER)
  await expect(host.locator('#foreign')).toBeVisible(); await host.waitForTimeout(250)
  await send(chat, 'Lan still signed in')
  await expect(chat.getByTestId('chat-mine')).toHaveText(['Lan private order', 'Lan still signed in'])
  await host.locator('#foreign').evaluate(node => node.remove())
  await api(host, 'logout'); await expect(chat.getByTestId('chat-mine')).toHaveText(['Anonymous order'])
  await host.evaluate(({ slug, logo }) => { const widget = window.Superstep as import('../src/widget/protocol').WidgetAPI; widget.init({ slug, language: 'vi', position: 'left', color: '#0f766e', logo }); widget.close(); widget.open() }, { slug, logo: LOGO })
  await expect(host.locator('#superstep-chat-button')).toHaveAttribute('aria-label', 'Đóng chat')
  await expect(chat.locator('#chat-input')).toHaveAttribute('placeholder', /^Nhập tin nhắn…/)
  await chat.locator('#chat-input').fill('Bạn có thể giúp tôi?')
  if (process.env.REVIEW_SHOTS) await host.screenshot({ animations: 'disabled', path: `${process.env.REVIEW_SHOTS}/widget-vi-custom.png` })
  await host.emulateMedia({ colorScheme: 'dark' })
  await expect(chat.locator('.superstep-chat').first()).toHaveAttribute('data-color-scheme', 'dark')
  await expect.poll(() => chat.locator('#public-chat').evaluate(el => [...el.querySelectorAll('#chat-input, #public-chat-new, #public-chat-sessions')]
    .every(control => getComputedStyle(control).color === getComputedStyle(el).color))).toBe(true)
  if (process.env.REVIEW_SHOTS) await host.screenshot({ animations: 'disabled', path: `${process.env.REVIEW_SHOTS}/widget-vi-dark.png` })
  const state = await host.evaluate(() => ({ events: (window as any).events, storage: { ...localStorage }, frame: document.querySelector('#superstep-chat-panel iframe')!.getAttribute('src') }))
  expect(state.events.filter((e: any) => e.name === 'message')).toHaveLength(4)
  expect(state.events.filter((e: any) => e.name === 'answer')).toHaveLength(4)
  expect(state.events.some((e: any) => e.name === 'open')).toBe(true); expect(state.events.some((e: any) => e.name === 'close')).toBe(true)
  expect(state.storage[`superstep-chat:${slug}`]).toBe(guest)
  const serialized = JSON.stringify(state); expect(serialized).not.toContain(mint('lan')); expect(serialized).not.toContain('Bearer ')
  expect(Object.values(state.storage)).toEqual([guest])
  await context.close()
})
test('widget preserves the backend app-key origin restriction and reports a safe error', async ({ page, browser }) => {
  const { slug, mint } = await fixture(page, [HOST]) // HTTP/socket originate in the Studio iframe, which this key refuses
  const context = await browser.newContext(), host = await context.newPage()
  await host.route(`${HOST}/**`, route => route.fulfill({ contentType: 'text/html', body: `<script src="${STUDIO}/c/widget.js" data-slug="${slug}" data-open="true"></script>` }))
  await host.goto(`${HOST}/origin`)
  const result = await host.evaluate(async token => { try { await (window.Superstep as import('../src/widget/protocol').WidgetAPI).identify(token); return 'unexpected' } catch (error) { return (error as { code: string }).code } }, mint('lan'))
  expect(result).toBe('CHAT_ORIGIN_FORBIDDEN')
  await expect(host.frameLocator('iframe').getByRole('alert')).toBeVisible()
  await context.close()
})

test('plain iframe exposes the native API and keeps user tokens out of storage', async ({ page, browser }) => {
  const { slug, mint } = await fixture(page)
  const context = await browser.newContext(), host = await context.newPage()
  await host.route(`${HOST}/**`, route => route.fulfill({ contentType: 'text/html', body: `<iframe id="native" src="${STUDIO}/c/${slug}?embed=1" style="width:420px;height:640px"></iframe>` }))
  await host.goto(`${HOST}/native`)
  const chat = host.frameLocator('#native')
  await expect(chat.locator('#chat-input')).toBeEnabled()
  const frame = host.frames().find(frame => frame.url().includes(`/c/${slug}`))!
  await frame.evaluate(async token => { await (window.Superstep as import('../src/widget/protocol').WidgetAPI).identify(token) }, mint('native-lan'))
  await send(chat, 'Native private order')
  await frame.evaluate(async () => { await (window.Superstep as import('../src/widget/protocol').WidgetAPI).logout() })
  await expect(chat.getByTestId('chat-mine')).toHaveCount(0)
  const values = await frame.evaluate(() => Object.values(localStorage))
  expect(values.some(value => value.split('.').length === 3)).toBe(false)
  await context.close()
})
