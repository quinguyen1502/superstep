import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createHmac } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { readFile } from 'node:fs/promises'
import { createServer } from 'node:net'

let port, origin
const secret = 'synthetic-host-test-secret-not-a-real-key'
let child
const api = (url, options = {}) => fetch(origin + url, { ...options, headers: { Origin: origin, ...options.headers } })
before(async () => {
  const probe = createServer()
  await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve))
  port = probe.address().port
  origin = `http://localhost:${port}`
  await new Promise(resolve => probe.close(resolve))
  child = spawn(process.execPath, [fileURLToPath(new URL('../server.mjs', import.meta.url))], { env: { ...process.env,
    CHAT_HOST_DEMO: '1', CHAT_HOST_PORT: String(port), CHAT_STUDIO_URL: 'http://127.0.0.1:8131', CHAT_SLUG: 'sample-test',
    CHAT_KEY_ID: 'ck_synthetic_host', CHAT_KEY_SECRET: secret }, stdio: ['ignore', 'pipe', 'pipe'] })
  await new Promise((resolve, reject) => {
    child.stdout.once('data', resolve)
    child.once('error', reject)
    child.once('exit', () => reject(new Error('Sample host exited before binding its port')))
  })
  for (let i = 0; i < 100; i++) {
    if (await api('/health').then(response => response.ok).catch(() => false)) return
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  throw new Error('Sample host did not start')
})
after(() => child?.kill('SIGTERM'))

test('host sign-in stub is explicit, bounded and server-owned', async () => {
  let response = await api('/api/auth/chat-token', { method: 'POST' })
  assert.equal(response.status, 401)
  response = await api('/api/auth/login', { method: 'POST', headers: { Origin: 'http://untrusted.test' }, body: JSON.stringify({ persona: 'lan' }) })
  assert.equal(response.status, 403)
  for (const data of [{ persona: '__proto__' }, { persona: 'administrator' }, { persona: 'lan', userId: 'sample-minh' }]) {
    response = await api('/api/auth/login', { method: 'POST', body: JSON.stringify(data) })
    assert.equal(response.status, 400)
  }
  response = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ persona: 'lan' }) })
  assert.equal(response.status, 200)
  const setCookie = response.headers.get('set-cookie')
  assert.equal(setCookie.includes('HttpOnly') && setCookie.includes('SameSite=Lax'), true)
  const cookie = setCookie.split(';')[0]
  response = await api('/api/auth/chat-token', { method: 'POST', headers: { Cookie: cookie }, body: JSON.stringify({ userId: 'sample-minh', slug: 'other' }) })
  assert.equal(response.status, 200)
  assert.equal(response.headers.get('cache-control'), 'no-store')
  const token = (await response.json()).data.token
  const [header, payload, signature] = token.split('.')
  const claims = JSON.parse(Buffer.from(payload, 'base64url'))
  assert.equal(claims.sub, 'sample-lan')
  assert.equal(claims.aud, 'superstep-chat:sample-test')
  assert.equal(claims.exp - claims.iat, 120)
  assert.equal(createHmac('sha256', secret).update(header + '.' + payload).digest('base64url') === signature, true)
  response = await api('/api/auth/session', { headers: { Cookie: cookie } })
  const session = await response.json()
  assert.equal(Object.hasOwn(session.data.config, 'secret') || Object.hasOwn(session.data.config, 'keyId') || Object.hasOwn(session.data, 'token'), false)
  response = await api('/api/auth/logout', { method: 'POST', headers: { Cookie: cookie } })
  assert.equal(response.status, 200)
  assert.equal((await api('/api/auth/chat-token', { method: 'POST', headers: { Cookie: cookie } })).status, 401)
})

test('normal startup refuses without explicit demo opt-in and does not echo secrets', async () => {
  const processResult = spawn(process.execPath, [fileURLToPath(new URL('../server.mjs', import.meta.url))], {
    env: { ...process.env, CHAT_HOST_DEMO: '0', CHAT_KEY_SECRET: secret }, stdio: ['ignore', 'ignore', 'pipe'] })
  let stderr = ''
  processResult.stderr.on('data', data => { stderr += data })
  const exit = await new Promise(resolve => processResult.on('close', resolve))
  assert.notEqual(exit, 0)
  assert.equal(stderr.includes(secret), false)
})

test('sample locales match and static serving cannot expose server sources', async () => {
  const en = JSON.parse(await readFile(new URL('../src/locales/en.json', import.meta.url), 'utf8'))
  const vi = JSON.parse(await readFile(new URL('../src/locales/vi.json', import.meta.url), 'utf8'))
  const keys = (value, prefix = '') => Object.entries(value).flatMap(([key, item]) => typeof item === 'object' ? keys(item, prefix + key + '.') : [prefix + key]).sort()
  assert.deepEqual(keys(en), keys(vi))
  assert.equal((await api('/..%2fserver.mjs')).status, 404)
  const response = await api('/')
  assert.equal(response.status, 200)
  assert.equal(response.headers.get('content-security-policy').includes("frame-ancestors 'none'"), true)
})
