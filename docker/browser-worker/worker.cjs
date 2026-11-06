// Private worker control only. Page code has no TCP/control endpoint or filesystem capability.
const http = require('node:http')
const net = require('node:net')
const crypto = require('node:crypto')
const { isDeepStrictEqual } = require('node:util')
const Ajv = require('ajv/dist/2020')
const { chromium } = require('playwright-core')
const schemas = require('./contracts.json')
const ajv = new Ajv({ strict: true, allErrors: false, coerceTypes: false, useDefaults: false })
const validators = Object.fromEntries(Object.entries(schemas).map(([name, schema]) => [name, ajv.compile(schema)]))
const clip = (value, length) => Array.from(String(value || '')).slice(0, length).join('')
const canonical = value => value && typeof value === 'object'
  ? Array.isArray(value) ? value.map(canonical) : Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value
const fingerprint = value => crypto.createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex')
const state = { browser: null, context: null, page: null, open: null, generation: 1, pageGeneration: 0,
  sequence: 0, observation: null, elements: new Map(), approvals: new Set(), artifacts: new Map(),
  secrets: [], busy: false, status: 'new', started: Date.now(), touched: Date.now(), denied: 0 }

function permitted(value) {
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return false
    const origins = state.open.settings.allowed_origins
    return !origins.length || origins.some(item => new URL(item).origin === url.origin)
  } catch { return false }
}
function identity(value) {
  return state.open && isDeepStrictEqual(value.context, state.open.context)
    && value.session_id === state.open.session_id && value.generation === state.generation
}
async function invalidate() {
  state.observation = null
  const handles = [...state.elements.values()].map(item => item.handle)
  state.elements.clear()
  await Promise.allSettled(handles.map(handle => handle.dispose()))
}
async function shutdown(status = 'session_lost') {
  state.status = status
  state.artifacts.clear(); state.approvals.clear()
  await invalidate()
  const browser = state.browser
  state.browser = null
  if (browser) await browser.close().catch(() => {})
}
async function expireIfNeeded() {
  const now = Date.now()
  if (state.status === 'ready' && ((!state.busy && now - state.touched >= state.open.settings.idle_timeout_s * 1000)
      || now - state.started >= state.open.settings.lifetime_s * 1000)) await shutdown('expired')
}
function profileState(value) {
  const profile = value.settings.profile, seed = value.profile_seed
  if (!profile) { if (seed) throw new Error('profile'); return undefined }
  if (!seed || seed.principal_id !== value.context.principal_id) throw new Error('profile')
  const origins = profile.origins, hosts = new Set()
  for (const origin of origins) {
    const url = new URL(origin)
    if (url.protocol !== 'https:' || url.origin !== origin || url.hostname.endsWith('.')) throw new Error('profile')
    hosts.add(url.hostname)
  }
  const seen = new Set()
  for (const cookie of seed.state.cookies) {
    const key = JSON.stringify([cookie.domain, cookie.path, cookie.name])
    if (!hosts.has(cookie.domain) || cookie.domain.startsWith('.') || cookie.secure !== true || seen.has(key)
        || (cookie.expires !== -1 && cookie.expires <= Date.now() / 1000) || /[\x00-\x1f\x7f;]/.test(cookie.value)) throw new Error('profile')
    seen.add(key)
  }
  seen.clear()
  for (const item of seed.state.origins) {
    if (!origins.includes(item.origin) || seen.has(item.origin) || new Set(item.localStorage.map(x => x.name)).size !== item.localStorage.length) throw new Error('profile')
    seen.add(item.origin)
  }
  if (Buffer.byteLength(JSON.stringify(seed)) > 64 * 1024 || !isDeepStrictEqual(value.settings.allowed_origins, origins)) throw new Error('profile')
  state.secrets = [...seed.state.cookies.map(x => x.value), ...seed.state.origins.flatMap(x => x.localStorage.map(y => y.value))].filter(Boolean).sort((a, b) => b.length - a.length)
  return seed.state
}
function safeText(value, length) {
  let text = String(value || '')
  for (const secret of state.secrets) text = text.split(secret).join('[redacted]')
  return clip(text, length)
}
async function open(value) {
  if (state.status !== 'new' || value.settings.provider !== 'local') throw new Error('unsupported')
  const storageState = profileState(value)
  state.open = value; state.generation = value.generation; state.started = state.touched = Date.now()
  state.browser = await chromium.launch({ headless: true, chromiumSandbox: true, proxy: { server: 'http://127.0.0.1:3128' } })
  state.context = await state.browser.newContext({ viewport: { width: 1024, height: 768 }, serviceWorkers: 'block', acceptDownloads: false, storageState })
  await state.context.route('**/*', route => {
    if (!permitted(route.request().url())) { state.denied++; return route.abort('blockedbyclient') }
    return route.continue()
  })
  await state.context.routeWebSocket('**/*', route => {
    const target = route.url().replace(/^ws:/, 'http:').replace(/^wss:/, 'https:')
    if (!permitted(target)) { state.denied++; return route.close() }
    route.connectToServer()
  })
  state.page = await state.context.newPage()
  state.context.on('page', page => { if (page !== state.page) page.close().catch(() => {}) })
  state.page.on('dialog', dialog => dialog.dismiss().catch(() => {}))
  state.page.on('download', download => download.cancel().catch(() => {}))
  state.page.on('framenavigated', frame => {
    if (frame === state.page.mainFrame()) { state.pageGeneration++; invalidate().catch(() => {}) }
  })
  state.browser.on('disconnected', () => { if (state.status === 'ready') state.status = 'session_lost' })
  state.status = 'ready'
  return { status: 'ready', session_id: value.session_id, generation: state.generation }
}
async function describe(handle) {
  return handle.evaluate(element => {
    const tag = element.tagName.toLowerCase()
    const clone = element.cloneNode(true)
    clone.querySelectorAll('input,textarea,select,[contenteditable],script,style').forEach(item => item.remove())
    const text = ['input', 'textarea', 'select'].includes(tag) || element.isContentEditable
      ? element.getAttribute('aria-label') || element.getAttribute('name') || '' : clone.textContent || ''
    return { role: element.getAttribute('role') || (tag === 'a' ? 'link' : tag === 'input' || tag === 'textarea' ? 'textbox' : tag),
      text: Array.from(text.replace(/\s+/g, ' ').trim()).slice(0, 1000).join(''),
      identity: [tag, element.getAttribute('type'), element.getAttribute('href'), element.getAttribute('role'),
        element.getAttribute('aria-label'), element.form?.action || '', element.form?.method || '', text.slice(0, 1000)] }
  })
}
async function snapshot() {
  await invalidate()
  const generation = state.pageGeneration
  const candidates = state.page.locator('h1,h2,h3,p,a,button,label,li,td,th,summary,input,textarea,select,[role]')
  const count = Math.min(400, await candidates.count())
  const elements = []
  try {
    for (let index = 0; index < count && elements.length < 200; index++) {
      const handle = await candidates.nth(index).elementHandle()
      if (!handle || !await handle.isVisible()) { await handle?.dispose(); continue }
      const item = await describe(handle)
      const element_id = crypto.randomUUID()
      state.elements.set(element_id, { handle, fingerprint: fingerprint(item.identity) })
      elements.push({ element_id, role: clip(item.role, 80), text: safeText(item.text, 1000) })
    }
    if (generation !== state.pageGeneration) throw new Error('stale')
    const url = new URL(state.page.url())
    if (!permitted(url.href)) throw new Error('policy')
    state.observation = crypto.randomUUID()
    return { observation_id: state.observation, page_generation: Math.max(1, generation), origin: url.origin,
      text: clip(elements.map(item => item.text).join('\n'), 16000), elements }
  } catch (error) { await invalidate(); throw error }
}
async function element(arguments_) {
  if (!state.observation || arguments_.observation_id !== state.observation) throw new Error('stale')
  const item = state.elements.get(arguments_.element_id)
  if (!item || !await item.handle.isVisible() || fingerprint((await describe(item.handle)).identity) !== item.fingerprint) throw new Error('stale')
  return item.handle
}
async function execute(command) {
  const start = Date.now()
  const result = { version: 1, command_id: command.command_id, generation: state.generation,
    sequence: command.sequence, status: 'confirmed', elapsed_ms: 0 }
  const finish = status => {
    result.status = status; result.elapsed_ms = Math.min(60000, Date.now() - start)
    // Keep finite UTF-8 JSON below the shared transport budget, even for emoji-heavy pages.
    while (Buffer.byteLength(JSON.stringify(result)) > 256 * 1024 && result.observation?.elements.length) result.observation.elements.pop()
    if (!validators.WorkerResult(result) || Buffer.byteLength(JSON.stringify(result)) > 256 * 1024) throw new Error('result')
    return result
  }
  if (!identity(command)) throw new Error('authority')
  if (state.status !== 'ready') return finish(['expired', 'session_lost', 'cancelled'].includes(state.status) ? state.status : 'session_lost')
  if (state.busy || command.sequence !== state.sequence) return finish('stale_observation')
  if (state.sequence >= state.open.settings.max_actions) { await shutdown('expired'); return finish('expired') }
  const effect = ['click', 'fill'].includes(command.operation)
  if (effect && !state.approvals.has(fingerprint(command))) return finish('approval_required')
  state.busy = true; state.touched = Date.now(); state.sequence++
  state.approvals.delete(fingerprint(command))
  const timeout = Math.min(command.timeout_ms, state.open.settings.action_timeout_ms)
  state.page.setDefaultTimeout(timeout); state.page.setDefaultNavigationTimeout(timeout)
  let timer
  try {
    const work = async () => {
      const args = command.arguments
      if (command.operation === 'navigate') {
        if (/[\x00-\x20\x7f\\]/.test(args.url) || !permitted(args.url)) throw new Error('policy')
        await invalidate()
        const response = await state.page.goto(args.url, { waitUntil: 'domcontentloaded', timeout })
        if (await response?.headerValue('x-superstep-egress') === 'denied') throw new Error('policy')
        if ([403, 429].includes(response?.status())) return 'challenge_required'
        result.observation = await snapshot()
      } else if (command.operation === 'snapshot') result.observation = await snapshot()
      else if (effect) {
        const handle = await element(args)
        if (command.operation === 'click') await handle.click({ timeout })
        else await handle.fill(args.value, { timeout })
        state.pageGeneration++; await invalidate()
      } else if (command.operation === 'extract') {
        result.extracted = {}
        for (const [name, element_id] of Object.entries(args.fields)) {
          const handle = await element({ observation_id: args.observation_id, element_id })
          result.extracted[name] = safeText((await describe(handle)).text, 4000)
        }
      } else if (command.operation === 'screenshot') {
        if (state.artifacts.size >= 4) throw new Error('limit')
        const bytes = await state.page.screenshot({ type: 'png', fullPage: false, mask: [state.page.locator('input,textarea,select,[contenteditable]'), ...state.secrets.map(secret => state.page.getByText(secret, { exact: false }))], timeout })
        if (bytes.length > 2 * 1024 * 1024) throw new Error('limit')
        result.artifact_id = crypto.randomUUID(); state.artifacts.set(result.artifact_id, bytes)
      }
      return 'confirmed'
    }
    const expiry = new Promise(resolve => { timer = setTimeout(() => {
      shutdown('session_lost').catch(() => {}); setTimeout(() => process.exit(0), 1000).unref(); resolve('unknown')
    }, timeout) })
    return finish(await Promise.race([work(), expiry]))
  } catch (error) {
    if (effect && !['policy', 'stale'].includes(error.message)) shutdown('session_lost').catch(() => {})
    return finish(error.message === 'policy' ? 'policy_denied' : error.message === 'stale' ? 'stale_observation' : effect ? 'unknown' : 'failed_before_effect')
  } finally { clearTimeout(timer); state.busy = false; state.touched = Date.now() }
}

const paths = { '/v1/open': 'WorkerOpen', '/v1/command': 'WorkerCommand', '/v1/approve': 'WorkerCommand',
  '/v1/artifact': 'WorkerArtifact', '/v1/close': 'WorkerControl' }
const server = http.createServer(async (request, response) => {
  const send = (status, result) => { response.writeHead(status, { 'content-type': 'application/json' }); response.end(JSON.stringify(result)) }
  if (request.method !== 'POST' || !paths[request.url]) return send(404, { status: 'invalid' })
  const chunks = []; let size = 0
  try {
    for await (const chunk of request) { size += chunk.length; if (size > 256 * 1024) return send(413, { status: 'invalid' }); chunks.push(chunk) }
    const value = JSON.parse(Buffer.concat(chunks).toString('utf8'))
    if (!validators[paths[request.url]](value)) return send(400, { status: 'invalid' })
    if (request.url === '/v1/open') return send(200, await open(value))
    if (!identity(value)) return send(403, { status: 'denied' })
    await expireIfNeeded()
    if (request.url === '/v1/command') return send(200, await execute(value))
    if (request.url === '/v1/approve') {
      if (state.status !== 'ready' || state.busy || value.sequence !== state.sequence || !['click', 'fill'].includes(value.operation)) return send(409, { status: 'stale' })
      await element(value.arguments)
      state.approvals.clear(); state.approvals.add(fingerprint(value)); return send(200, { status: 'approved' })
    }
    if (request.url === '/v1/artifact') {
      const bytes = state.artifacts.get(value.artifact_id)
      if (!bytes || state.status !== 'ready') return send(404, { status: 'missing' })
      return send(200, { artifact_id: value.artifact_id, png: bytes.toString('base64') })
    }
    await shutdown('cancelled'); send(200, { status: 'closed' }); setTimeout(() => process.exit(0), 100).unref()
  } catch { send(400, { status: 'invalid' }) }
})
server.requestTimeout = 15000; server.headersTimeout = 15000
const bridge = net.createServer(client => {
  const upstream = net.createConnection('/egress/gateway.sock')
  client.on('error', () => upstream.destroy()); upstream.on('error', () => client.destroy())
  client.pipe(upstream).pipe(client)
})
bridge.listen(3128, '127.0.0.1')
server.listen('/tmp/browser-control.sock', () => require('node:fs').chmodSync('/tmp/browser-control.sock', 0o600))
setInterval(() => {
  const now = Date.now()
  expireIfNeeded().catch(() => {})
  if (now - state.started > (state.open?.settings.lifetime_s || 30) * 1000 + 5000) process.exit(0)
}, 1000).unref()
process.on('SIGTERM', () => { shutdown('cancelled').finally(() => process.exit(0)); setTimeout(() => process.exit(0), 1000).unref() })
