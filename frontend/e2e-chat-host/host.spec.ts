import { test, expect } from '@playwright/test'
import type { Page, TestInfo } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import hostVi from '../../examples/chat-host/src/locales/vi.json' with { type: 'json' }
import { startsWith } from '../e2e/catalog'

const configFile = process.env.CHAT_HOST_FIXTURE
if (!configFile) throw new Error('Run scripts/chat_host_e2e.sh to seed an isolated backend')
const config = JSON.parse(await fs.readFile(configFile, 'utf8'))
const host = `http://localhost:${process.env.CHAT_HOST_PORT || 5188}`
const secondary = `http://localhost:${process.env.CHAT_HOST_SECOND_PORT || 5189}`
const studio = config.baseUrl

async function signIn(page: Page, persona: 'lan' | 'minh') {
  await page.goto('/')
  await page.getByTestId(`signin-${persona}`).click()
  await expect(page.getByTestId('stream-status')).toHaveAttribute('data-state', 'idle')
}
async function screenshot(page: Page, name: string, testInfo: TestInfo) {
  const file = testInfo.outputPath(`${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  await testInfo.attach(name, { path: file, contentType: 'image/png' })
}

test('cross-origin customer flow: form, file, rating, two-user isolation, origins and revoke', async ({ browser, page, request }, testInfo) => {
  const consoleErrors: string[] = []
  page.on('pageerror', error => consoleErrors.push(error.name))
  page.on('requestfailed', req => { if (req.url().startsWith(studio)) console.log('Studio request failed:', req.method(), req.failure()?.errorText) })
  const frames: string[] = []
  page.on('websocket', socket => {
    expect(new URL(socket.url()).search).toBe('')
    socket.on('framereceived', event => {
      const data = JSON.parse(String(event.payload))
      if (typeof data.type === 'string') frames.push(data.type)
    })
  })
  const leakedCookies: boolean[] = []
  page.on('request', req => { if (req.url().startsWith(studio)) leakedCookies.push(Boolean(req.headers()['cookie'])) })
  expect(new URL(host).origin).not.toBe(new URL(studio).origin)
  const unauthenticated = await request.post(host + '/api/auth/chat-token', { headers: { Origin: host } })
  expect(unauthenticated.status()).toBe(401)
  const csrf = await request.post(host + '/api/auth/login', { headers: { Origin: secondary }, data: { persona: 'lan' } })
  expect(csrf.status()).toBe(403)
  const arbitrary = await request.post(host + '/api/auth/login', { headers: { Origin: host }, data: { persona: 'lan', userId: 'sample-minh' } })
  expect(arbitrary.status()).toBe(400)

  await signIn(page, 'lan')
  const probeToken = (await (await page.request.post(host + '/api/auth/chat-token', { headers: { Origin: host } })).json()).data.token
  const probe = await request.get(`${studio}/api/public/v1/chat/${config.human.slug}/sessions`, { headers: { Origin: host, Authorization: `Bearer ${probeToken}` } })
  expect(probe.status()).toBe(200)
  expect(probe.headers()['access-control-allow-origin']).toBe(host)
  const preflight = await request.fetch(`${studio}/api/public/v1/chat/${config.human.slug}/sessions`, { method: 'OPTIONS', headers: { Origin: host, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type' } })
  expect(preflight.status()).toBe(204)
  const sessionCookie = (await page.context().cookies()).find(cookie => cookie.name === 'superstep_chat_host')
  expect(Boolean(sessionCookie?.httpOnly && sessionCookie.sameSite === 'Lax')).toBe(true)
  const unique = 'Please review this sample request.'
  await page.getByLabel('Attach a document', { exact: true }).setInputFiles({ name: 'sample-note.txt', mimeType: 'text/plain', buffer: Buffer.from('Sample attachment for the chat host') })
  await page.getByLabel('Your message', { exact: true }).fill(unique)
  await page.getByRole('button', { name: 'Send message', exact: true }).click()
  await expect(page.getByTestId('approval-form')).toBeVisible()
  await page.getByLabel('I approve this request', { exact: true }).check()
  await page.getByLabel('Your note', { exact: true }).fill('Confirmed by the sample customer')
  await page.getByRole('button', { name: 'Send answer', exact: true }).click()
  await expect(page.getByTestId('stream-status')).toHaveAttribute('data-state', 'idle')
  await expect(page.getByTestId('messages')).toContainText('approved: true')
  await expect(page.getByTestId('messages')).toContainText('sample-note.txt')
  expect(frames).toContain('token'); expect(frames).toContain('question'); expect(frames).toContain('done')
  expect(leakedCookies.length > 0 && leakedCookies.every(value => !value)).toBe(true)
  await page.getByRole('button', { name: 'Helpful answer', exact: true }).last().click()
  await expect(page.getByText('Feedback saved', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'New conversation', exact: true })).toBeEnabled()
  const sid = await page.getByTestId('messages').getAttribute('data-session-id')
  expect(Boolean(sid)).toBe(true)

  await screenshot(page, 'host-en-light', testInfo)
  await page.getByRole('button', { name: 'Switch colour theme', exact: true }).click()
  await screenshot(page, 'host-en-dark', testInfo)
  await page.getByRole('button', { name: 'Tiếng Việt', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Tiếng Việt', exact: true })).toHaveAttribute('data-variant', 'secondary')
  await expect(page.getByText(hostVi.rated, { exact: true })).toBeVisible()
  await screenshot(page, 'host-vi-dark', testInfo)
  await page.getByRole('button', { name: hostVi.theme, exact: true }).click()
  await screenshot(page, 'host-vi-light', testInfo)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false)
  await screenshot(page, 'host-mobile', testInfo)
  await page.setViewportSize({ width: 1280, height: 1000 })

  const otherContext = await browser.newContext({ locale: 'en-US' })
  const other = await otherContext.newPage()
  await other.goto(host)
  await other.getByTestId('signin-minh').click()
  await expect(other.getByTestId('stream-status')).toHaveAttribute('data-state', 'idle')
  await expect(other.getByTestId('conversation-list')).not.toContainText(unique)
  const otherToken = (await (await other.request.post(host + '/api/auth/chat-token', { headers: { Origin: host } })).json()).data.token
  const denied = await request.get(`${studio}/api/public/v1/chat/${config.human.slug}/sessions/${sid}`, { headers: { Origin: host, Authorization: `Bearer ${otherToken}` } })
  expect(denied.status()).toBe(404)

  const sameContext = await browser.newContext({ locale: 'en-US' })
  const restored = await sameContext.newPage()
  await restored.goto(host)
  await restored.getByTestId('signin-lan').click()
  await expect(restored.getByTestId('messages')).toContainText(unique)
  await expect(restored.getByText('Feedback saved', { exact: true })).toBeVisible()

  const forbiddenContext = await browser.newContext({ locale: 'en-US' })
  const forbiddenPage = await forbiddenContext.newPage()
  await forbiddenPage.goto(secondary)
  await forbiddenPage.getByTestId('signin-lan').click()
  await expect(forbiddenPage.getByRole('alert')).toBeVisible()
  const originDenied = await request.get(`${studio}/api/public/v1/chat/${config.human.slug}/sessions`, { headers: { Origin: secondary, Authorization: `Bearer ${otherToken}` } })
  expect(originDenied.status()).toBe(403)
  const socketCode = await forbiddenPage.evaluate(async ({ url, token, sid }) => new Promise<string>((resolve, reject) => {
    const socket = new WebSocket(url)
    const timer = setTimeout(() => { socket.close(); reject(new Error('Origin socket check timed out')) }, 5000)
    socket.onmessage = event => {
      const frame = JSON.parse(event.data)
      if (frame.type === 'ready') { socket.send(JSON.stringify({ type: 'auth', token })); socket.send(JSON.stringify({ type: 'message', chat_session_id: sid, text: 'must not execute' })) }
      if (frame.type === 'error') { clearTimeout(timer); socket.close(); resolve(frame.error.code) }
    }
  }), { url: studio.replace('http:', 'ws:') + `/ws/public/v1/chat/${config.human.slug}`, token: otherToken, sid: sid! })
  expect(socketCode).toBe('CHAT_ORIGIN_FORBIDDEN')

  const before = await request.get(`${studio}/api/workflows/${config.human.workflowId}/chat/visitors/${sid}`, { headers: { Authorization: `Bearer ${config.owner}` } })
  expect(before.ok()).toBe(true)
  const count = (await before.json()).data.turns.length
  const revoke = await request.delete(`${studio}/api/workflows/${config.human.workflowId}/chat/app-keys/${config.human.keyId}`, { headers: { Authorization: `Bearer ${config.owner}` } })
  expect(revoke.ok()).toBe(true)
  await restored.getByLabel('Your message', { exact: true }).fill('This must not run after revoke')
  await restored.getByRole('button', { name: 'Send message', exact: true }).click()
  await expect(restored.getByRole('alert')).toBeVisible()
  const after = await request.get(`${studio}/api/workflows/${config.human.workflowId}/chat/visitors/${sid}`, { headers: { Authorization: `Bearer ${config.owner}` } })
  expect((await after.json()).data.turns.length).toBe(count)
  await screenshot(restored, 'host-revoked-key', testInfo)
  expect(consoleErrors).toEqual([])

  const assets = await fs.readdir(path.resolve('examples/chat-host/dist/assets'))
  let leaked = false
  for (const name of assets.filter(name => name.endsWith('.js'))) {
    const text = await fs.readFile(path.resolve('examples/chat-host/dist/assets', name), 'utf8')
    leaked ||= text.includes(config.human.secret) || text.includes(config.owner)
  }
  expect(leaked).toBe(false)
  await Promise.all([otherContext.close(), sameContext.close(), forbiddenContext.close()])
})
