const assert = require('node:assert/strict')
const net = require('node:net')
const { chromium } = require('playwright-core')

// Local bridge forwards bytes only; the gateway parses/validates every target.
// network=none ensures Chromium cannot bypass this Unix socket path.
const bridge = net.createServer(client => {
  const upstream = net.createConnection('/egress/gateway.sock')
  client.on('error', () => upstream.destroy())
  upstream.on('error', () => client.destroy())
  client.pipe(upstream).pipe(client)
})
const checks = []
async function denied(page, url) {
  let blocked = false
  try { const response = await page.goto(url, { timeout: 4000 }); blocked = !response || response.status() === 403 }
  catch { blocked = true }
  assert.ok(blocked, `Expected denial: ${url}`)
  checks.push('denied')
}

;(async () => {
  await new Promise(resolve => bridge.listen(3128, '127.0.0.1', resolve))
  const browser = await chromium.launch({ headless: true, chromiumSandbox: true,
    proxy: { server: 'http://127.0.0.1:3128' } })
  try {
    // Secure-context service-worker code is blocked as an explicit runtime rule.
    // Only this disposable self-signed fixture ignores certificate errors.
    const context = await browser.newContext({ serviceWorkers: 'block', ignoreHTTPSErrors: true })
    const page = await context.newPage()
    assert.equal((await page.goto('http://allowed.test:8080/ok?token=synthetic-query-secret')).status(), 200)
    assert.match(await page.textContent('h1'), /allowed fixture/)
    checks.push('allowed')
    if (process.env.FIXTURE_ROUTE === 'direct') assert.equal((await page.goto('http://allowed.test:8082/direct-ok')).status(), 200)
    else await denied(page, 'http://allowed.test:8082/no-fallback')
    await page.goto('http://allowed.test:8080/hostile')
    await page.waitForTimeout(1000)
    assert.equal((await page.goto('https://allowed.test:8443/hostile')).status(), 200)
    assert.equal(await page.evaluate(() => window.isSecureContext && !!navigator.serviceWorker), true)
    await page.evaluate(() => Promise.race([
      navigator.serviceWorker.register('/sw.js').then(() => 'settled').catch(() => 'blocked'),
      new Promise(resolve => setTimeout(() => resolve('blocked'), 300))
    ]))
    assert.equal(context.serviceWorkers().length, 0)
    checks.push('secure-origin-service-worker-blocked')
    for (const url of ['http://127.0.0.1:9090/private', 'http://[::1]:8080/private',
      'http://169.254.169.254:8080/metadata', 'http://private.test:8080/private',
      'http://metadata.test:8080/metadata', 'http://mixed.test:8080/private', 'http://allowed.test:8080/redirect']) {
      await denied(page, url)
    }
    assert.equal((await page.goto('http://rebind.test:8080/ok')).status(), 200)
    await denied(page, 'http://rebind.test:8080/second')
    checks.push('rebind-blocked')
    await context.close()
  } finally { await browser.close() }
  // A browser launched without a proxy must not reach *any* container/host network.
  const direct = await chromium.launch({ headless: true, chromiumSandbox: true })
  try {
    const page = await direct.newPage()
    await denied(page, `http://${process.env.FIXTURE_IP}:8080/no-proxy`)
    await denied(page, 'http://host.docker.internal:8080/no-proxy')
    checks.push('no-direct-network')
  } finally { await direct.close() }
  console.log(JSON.stringify({ outcome: 'passed', checks }))
})().catch(error => { console.error(error.message); process.exitCode = 1 }).finally(() => bridge.close())
