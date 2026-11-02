// Local demonstration only: replace the sign-in stub with your application's authentication before deployment.
import http from 'node:http'
import { randomBytes } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { mintChatToken } from '../../sdk/typescript/dist/esm/server.js'

const root = process.env.CHAT_HOST_DIST ? path.resolve(process.env.CHAT_HOST_DIST) : path.join(path.dirname(fileURLToPath(import.meta.url)), 'dist')
const port = Number(process.env.CHAT_HOST_PORT || 5188)
const hostOrigin = `http://localhost:${port}`
const baseUrl = process.env.CHAT_STUDIO_URL || ''
const slug = process.env.CHAT_SLUG || ''
const keyId = process.env.CHAT_KEY_ID || ''
const secret = process.env.CHAT_KEY_SECRET || ''
const people = { lan: { id: 'sample-lan', name: 'Lan' }, minh: { id: 'sample-minh', name: 'Minh' } }
if (process.env.CHAT_HOST_DEMO !== '1' || ![baseUrl, slug, keyId, secret].every(Boolean) || !Number.isInteger(port) || port < 1024 || port > 65535) {
  throw new Error('Set CHAT_HOST_DEMO=1, CHAT_STUDIO_URL, CHAT_SLUG, CHAT_KEY_ID and CHAT_KEY_SECRET for this loopback-only sample')
}
let studio
try { studio = new URL(baseUrl) } catch { throw new Error('Invalid CHAT_STUDIO_URL') }
if (!['http:', 'https:'].includes(studio.protocol) || studio.username || studio.password || studio.search || studio.hash) throw new Error('Invalid CHAT_STUDIO_URL')
const wsOrigin = `${studio.protocol === 'https:' ? 'wss:' : 'ws:'}//${studio.host}`
const sessions = new Map()
const cookieName = 'superstep_chat_host'
const lifetime = 30 * 60_000
const fail = (status, code) => Object.assign(new Error(code), { status, code })
const errors = { AUTH_REQUIRED: 'Sign in to continue', BAD_REQUEST: 'Invalid request', PAYLOAD_TOO_LARGE: 'Request body too large',
  NOT_FOUND: 'Not found', CHAT_ORIGIN_FORBIDDEN: 'Request origin is not allowed', INTERNAL_ERROR: 'Internal server error' }
function json(res, status, data, error) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' })
  res.end(JSON.stringify({ success: !error, data: error ? null : data, error: error || null }))
}
function session(req) {
  const value = req.headers.cookie?.split(';').map(part => part.trim()).find(part => part.startsWith(cookieName + '='))?.slice(cookieName.length + 1)
  const entry = value && sessions.get(value)
  if (!entry || entry.expires <= Date.now()) { if (value) sessions.delete(value); return null }
  return { ...entry, key: value }
}
async function body(req) {
  let size = 0, parts = []
  for await (const chunk of req) {
    size += chunk.length
    if (size > 8192) throw fail(413, 'PAYLOAD_TOO_LARGE')
    parts.push(chunk)
  }
  try {
    const value = JSON.parse(Buffer.concat(parts).toString('utf8'))
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error()
    return value
  } catch { throw fail(400, 'BAD_REQUEST') }
}
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' }
const server = http.createServer(async (req, res) => {
  try {
    if (req.headers.host !== new URL(hostOrigin).host) throw fail(403, 'CHAT_ORIGIN_FORBIDDEN')
    const url = new URL(req.url || '/', hostOrigin)
    if (req.method !== 'GET' && (req.method !== 'POST' || req.headers.origin !== hostOrigin)) throw fail(403, 'CHAT_ORIGIN_FORBIDDEN')
    if (req.method === 'GET' && url.pathname === '/health') return json(res, 200, { ok: true })
    if (req.method === 'GET' && url.pathname === '/api/auth/session') return json(res, 200, { user: session(req)?.user || null, config: { baseUrl, slug } })
    if (req.method === 'POST' && url.pathname === '/api/auth/login') {
      const value = await body(req)
      const user = Object.hasOwn(people, value.persona) ? people[value.persona] : null
      if (!user || Object.keys(value).some(key => key !== 'persona')) throw fail(400, 'BAD_REQUEST')
      const old = session(req); if (old) sessions.delete(old.key)
      if (sessions.size >= 1000) sessions.delete(sessions.keys().next().value)
      const key = randomBytes(32).toString('hex')
      sessions.set(key, { user, expires: Date.now() + lifetime })
      res.setHeader('Set-Cookie', `${cookieName}=${key}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${lifetime / 1000}`)
      return json(res, 200, { user, config: { baseUrl, slug } })
    }
    if (req.method === 'POST' && url.pathname === '/api/auth/logout') {
      const current = session(req); if (current) sessions.delete(current.key)
      res.setHeader('Set-Cookie', `${cookieName}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`)
      return json(res, 200, { ok: true })
    }
    if (req.method === 'POST' && url.pathname === '/api/auth/chat-token') {
      const current = session(req)
      if (!current) throw fail(401, 'AUTH_REQUIRED')
      // User ID and name come only from our authenticated server-side session, never the request body.
      const token = await mintChatToken({ keyId, secret, slug, userId: current.user.id, name: current.user.name, ttl: 120 })
      return json(res, 200, { token })
    }
    if (url.pathname.startsWith('/api/') || req.method !== 'GET') throw fail(404, 'NOT_FOUND')
    const decoded = decodeURIComponent(url.pathname)
    const file = path.resolve(root, '.' + (decoded === '/' ? '/index.html' : decoded))
    if (!file.startsWith(root + path.sep) || !(await stat(file).catch(() => null))?.isFile()) throw fail(404, 'NOT_FOUND')
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store',
      'Content-Security-Policy': `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self' ${studio.origin} ${wsOrigin}; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`,
      'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' })
    res.end(await readFile(file))
  } catch (error) {
    const code = Object.hasOwn(errors, error.code) ? error.code : 'INTERNAL_ERROR'
    if (!res.headersSent) json(res, code === 'INTERNAL_ERROR' ? 500 : error.status || 500, null, { code, message: errors[code] })
    else res.end()
  }
})
server.listen(port, '127.0.0.1', () => console.log(`Chat host demo: ${hostOrigin}`))
const stop = () => server.close(() => process.exit(0))
process.on('SIGTERM', stop); process.on('SIGINT', stop)
