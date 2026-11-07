import { createHmac } from 'node:crypto'
import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
// TASK-0228: a native app (iOS WKWebView, Android WebView, React Native WebView) shows /c/{slug}?embed=1 as its top-level
// page. This browser test plays the native side: it injects the same message channel the app would add, answers the
// page's ready and token-request messages with Superstep.identify(token), and checks that no token reaches the URL.
// It does not run on a device; the Swift, Kotlin and React Native snippets in the handbook are not executed here.
test.use({ screenshot: 'off', trace: 'off' }) // user tokens must not appear in captures

const CHANNELS = {
  ios: 'window.webkit = { messageHandlers: { superstep: { postMessage: send } } }',
  android: 'window.superstep = { postMessage: send }',
  'react-native': 'window.ReactNativeWebView = { postMessage: send }',
} as const

for (const [kind, install] of Object.entries(CHANNELS)) {
  test(`a ${kind} host signs the user in through the native bridge`, async ({ page, browser }) => {
    const H = await login(page)
    const graph = SIMPLE('Native chat')
    const wid = await newWorkflow(page, H, { ...graph, state: [...graph.state, { name: 'chat', type: 'object' }] })
    const slug = `native-${kind}-${Date.now()}`, studio = new URL(page.url()).origin
    expect((await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, slug, access: ['app'], reply_field: 'answer' } })).ok()).toBe(true)
    const key = (await (await page.request.post(`/api/workflows/${wid}/chat/app-keys`, { headers: H, data: { label: 'Mobile app', origins: [studio] } })).json()).data
    const mint = () => {
      const now = Math.floor(Date.now() / 1000), part = (data: unknown) => Buffer.from(JSON.stringify(data)).toString('base64url')
      const unsigned = `${part({ alg: 'HS256', typ: 'JWT', kid: key.key_id })}.${part({ iss: key.key_id, aud: `superstep-chat:${slug}`, sub: 'mobile-user', iat: now, exp: now + 600 })}`
      return `${unsigned}.${createHmac('sha256', key.secret).update(unsigned).digest('base64url')}`
    }
    const tokens = [mint(), mint()]
    // A fresh context: the app's WebView has no studio session.
    const app = await (await browser.newContext({ locale: 'en-US' })).newPage()
    await app.addInitScript(({ install, tokens }) => {
      const w = window as unknown as { __native: string[]; Superstep?: { identify(token: string): Promise<void> } }
      w.__native = []
      let next = 0
      // The app answers the page's ready message and each token request with a short-lived token.
      const send = (message: string) => {
        w.__native.push(message)
        const data = JSON.parse(message)
        if (data.type === 'superstep-chat:ready' || data.type === 'superstep-chat:token-request') setTimeout(() => void w.Superstep?.identify(tokens[Math.min(next++, tokens.length - 1)]).catch(() => {}), 0)
      }
      new Function('send', install)(send)
    }, { install, tokens })
    await app.goto(`/c/${slug}?embed=1`)
    await app.locator('#chat-input').fill('hello from the app'); await app.locator('#chat-input').press('Enter')
    await expect(app.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    const sent: { v: number; type: string; slug: string }[] = (await app.evaluate(() => (window as unknown as { __native: string[] }).__native)).map(m => JSON.parse(m))
    expect(sent[0]).toEqual({ v: 1, type: 'superstep-chat:ready', slug })
    // useChat reads the token more than once: the second read is answered by the app, not by reusing the first token.
    expect(sent.filter(m => m.type === 'superstep-chat:token-request').length).toBeGreaterThan(0)
    for (const message of sent) expect(['superstep-chat:ready', 'superstep-chat:token-request']).toContain(message.type)
    // Tokens go into the page only through identify(); never the URL, the messages to the app or storage.
    for (const token of tokens) {
      expect(app.url()).not.toContain(token)
      expect(JSON.stringify(sent)).not.toContain(token)
      expect(await app.evaluate(() => JSON.stringify({ ...localStorage }))).not.toContain(token)
    }
    await app.context().close()
  })
}
