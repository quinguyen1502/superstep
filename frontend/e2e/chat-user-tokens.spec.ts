import { createHmac } from 'node:crypto'
import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'

test.use({ screenshot: 'off', trace: 'off' }) // the server-only app secret must never appear in captures

test('third-party bearer users chat across origins and revocation is immediate', async ({ page }) => {
  const H = await login(page)
  const graph = SIMPLE('Third-party chat')
  const wid = await newWorkflow(page, H, { ...graph, state: [...graph.state, { name: 'chat', type: 'object' }] })
  const slug = `external-${Date.now()}`, origin = new URL(page.url()).origin
  expect((await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, slug, access: ['anonymous', 'app'], reply_field: 'answer' } })).ok()).toBe(true)
  const key = (await (await page.request.post(`/api/workflows/${wid}/chat/app-keys`, { headers: H, data: { label: 'Test server', origins: [origin] } })).json()).data
  const mint = (sub: string) => {
    const now = Math.floor(Date.now() / 1000)
    const part = (data: unknown) => Buffer.from(JSON.stringify(data)).toString('base64url')
    const unsigned = `${part({ alg: 'HS256', typ: 'JWT', kid: key.key_id })}.${part({ iss: key.key_id, aud: `superstep-chat:${slug}`, sub, iat: now, exp: now + 600 })}`
    return `${unsigned}.${createHmac('sha256', key.secret).update(unsigned).digest('base64url')}`
  }
  // Only short-lived user tokens enter the browser. The secret stays in the test's server context.
  const a = mint('customer-a'), b = mint('customer-b')
  const base = `http://127.0.0.1:${process.env.E2E_API_PORT || 8100}/api/public/v1/chat/${slug}`
  expect(new URL(base).origin).not.toBe(origin)
  const start = (token: string) => page.evaluate(async ({ base, token }) => {
    const r = await fetch(`${base}/sessions`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, credentials: 'omit' })
    return { status: r.status, body: await r.json() }
  }, { base, token })
  const first = await start(a); expect(first.status).toBe(200)
  const sid = first.body.data.id
  const stream = await page.evaluate(({ url, token, sid }) => new Promise<any[]>((resolve, reject) => {
    const ws = new WebSocket(url), frames: any[] = []
    const timeout = setTimeout(() => { ws.close(); reject(new Error('chat stream timed out')) }, 15000)
    ws.onerror = () => { clearTimeout(timeout); reject(new Error('chat socket failed')) }
    ws.onmessage = e => {
      const f = JSON.parse(e.data); frames.push(f)
      if (f.type === 'ready') { ws.send(JSON.stringify({ type: 'auth', token })); ws.send(JSON.stringify({ type: 'message', chat_session_id: sid, text: 'hello' })) }
      if (f.type === 'done' || f.type === 'error') { clearTimeout(timeout); ws.close(); resolve(frames) }
    }
  }), { url: base.replace(/^http/, 'ws').replace('/api/public/v1/chat/', '/ws/public/v1/chat/'), token: a, sid })
  expect(stream.at(-1).type).toBe('done'); expect(stream.at(-1).status).toBe('ok')
  expect(stream.some(f => f.type === 'token')).toBe(true)
  const read = (token: string) => page.evaluate(async ({ base, sid, token }) => {
    const r = await fetch(`${base}/sessions/${sid}`, { headers: { Authorization: `Bearer ${token}` }, credentials: 'omit' })
    return { status: r.status, body: await r.json() }
  }, { base, sid, token })
  expect((await read(a)).status).toBe(200)
  const foreign = await read(b); expect(foreign.status).toBe(404); expect(foreign.body.error.code).toBe('CHAT_SESSION_NOT_FOUND')
  expect((await page.request.delete(`/api/workflows/${wid}/chat/app-keys/${key.key_id}`, { headers: H })).ok()).toBe(true)
  const revoked = await read(a); expect(revoked.status).toBe(401); expect(revoked.body.error.code).toBe('CHAT_APP_KEY_REVOKED')
})
