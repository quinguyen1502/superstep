// Captures docs/screenshots for states. Run: SHOTS=1 npm run e2e -- screenshots
import { test, expect, type Page } from '@playwright/test'
import { apiToken, signIn } from './helpers'
test.skip(!process.env.SHOTS, 'set SHOTS=1 to capture screenshots')
const out = (n: string) => `../docs/screenshots/${n}.png`
test.use({ viewport: { width: 1280, height: 800 } })

test('capture auth and list states', async ({ page, request }) => {
  const email = `shots-${Date.now()}@example.com`
  await page.goto('/login?expired=1&next=%2Fworkflows'); await expect(page.locator('#expired-notice')).toBeVisible()
  await page.screenshot({ path: out('auth-expired-notice') })
  await page.getByLabel('Mật khẩu', { exact: true }).fill('wrongpass1'); await page.locator('#auth-submit').click()
  await expect(page.locator('#auth-error')).toBeVisible(); await expect(page.locator('#auth-submit')).toBeEnabled(); await page.mouse.move(0, 0); await page.waitForTimeout(400)
  await page.screenshot({ path: out('auth-login-error') })
  await page.goto('/register'); await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill('abcdefg'); await page.getByLabel('Xác nhận mật khẩu').fill('abcdefx')
  await page.screenshot({ path: out('auth-register-password-rules') })
  const r = await request.post('/api/auth/register', { data: { email, password: 'goodpass1' } }); const { token } = (await r.json()).data
  const H = { Authorization: `Bearer ${token}` }
  for (const w of (await (await request.get('/api/workflows', { headers: H })).json()).data) await request.delete(`/api/workflows/${w.id}?force=true`, { headers: H })
  await signIn(page, email, 'goodpass1')
  await page.goto('/workflows'); await expect(page.locator('#wf-empty')).toBeVisible(); await page.screenshot({ path: out('list-empty-state') })
  await request.post('/api/workflows', { headers: H, data: { name: 'A very long workflow name that keeps going to show truncation in the list view without breaking the table layout at all', nodes: [], edges: [] } })
  await request.post('/api/workflows', { headers: H, data: { name: 'Support triage', nodes: [], edges: [] } })
  await page.reload(); await page.screenshot({ path: out('list-long-names') })
  await page.locator('.wf-actions').first().click(); await page.getByRole('menuitem', { name: 'Đổi tên', exact: true }).click()
  await page.locator('#rename-input').fill('   '); await page.screenshot({ path: out('list-rename-empty-error') }); await page.keyboard.press('Escape')
  await page.locator('#wf-search').fill('nothing matches'); await expect(page.locator('#wf-no-results')).toBeVisible()
  await page.screenshot({ path: out('list-search-no-results') })
  await page.evaluate(() => localStorage.setItem('theme', 'dark')); await page.reload(); await page.locator('#wf-search').fill('nothing matches')
  await page.screenshot({ path: out('list-search-no-results-dark') })
  await page.evaluate(() => localStorage.setItem('theme', 'light'))
  await page.goto('/workflows/doesnotexist'); await expect(page.locator('#editor-not-found')).toBeVisible()
  await page.screenshot({ path: out('editor-not-found') })
})

test.describe('trace', () => {
  test.use({ viewport: { width: 1440, height: 900 } })
  test('capture run trace timeline states', async ({ page }) => {
    await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    await page.goto('/workflows/example'); await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    await page.mouse.move(5, 5); await page.waitForTimeout(400)
    await page.screenshot({ path: out('trace-timeline') })
    await page.locator('.react-flow__node[data-id="classify"]').click(); await expect(page.locator('#trace-diff')).toBeVisible()
    await page.mouse.move(5, 5); await page.waitForTimeout(300)
    await page.screenshot({ path: out('trace-detail-diff') })
    await page.getByRole('button', { name: /dark mode/i }).click(); await page.waitForTimeout(400); await page.mouse.move(5, 5)
    await page.screenshot({ path: out('trace-dark') })
    await page.getByRole('button', { name: /light mode|dark mode/i }).click()
    const token = await apiToken(page)
    const loop = {
      name: 'Loop demo (recursion limit)', state: [{ name: 'message', type: 'string' }, { name: 'intent', type: 'string' }],
      nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
        { id: 'think', type: 'llm', position: { x: 260, y: 150 }, data: { label: 'Think', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
        { id: 'check', type: 'condition', position: { x: 500, y: 150 }, data: { label: 'Check done?', field: 'intent', default: 'again' } },
        { id: 'e', type: 'end', position: { x: 740, y: 150 }, data: { label: 'End' } }],
      edges: [{ id: '1', source: 's', target: 'think' }, { id: '2', source: 'think', target: 'check' },
        { id: '3', source: 'check', target: 'think', label: 'again' }, { id: '4', source: 'check', target: 'e', label: 'done' }],
    }
    const r = await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: loop })
    await page.goto(`/workflows/${(await r.json()).data.id}`); await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'error', { timeout: 30_000 })
    await page.locator('.trace-row.bg-destructive\\/5').click(); await page.mouse.move(5, 5); await page.waitForTimeout(300)
    await page.screenshot({ path: out('trace-loop-or-error') })
  })
})

test.describe('node colors', () => {
  test.use({ viewport: { width: 1440, height: 900 } })
  test('capture node-type colours light/dark', async ({ page }) => {
    await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
    await expect(page).toHaveURL(/\/workflows$/)
    const token = await apiToken(page)
    const n = (id: string, type: string, x: number, y: number, data: object) => ({ id, type, position: { x, y }, data })
    const wf = { name: 'All node types', state: [{ name: 'message', type: 'string' }, { name: 'intent', type: 'string' }],
      nodes: [n('start', 'start', 40, 200, { label: 'Start' }), n('llm', 'llm', 280, 200, { label: 'Classify', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'intent' }),
        n('cond', 'condition', 520, 200, { label: 'Route', field: 'intent', default: 'general' }), n('tool', 'tool', 780, 80, { label: 'Lookup order', mode: 'function', function: 'lookup_order', output_field: 'message' }),
        n('code', 'code', 780, 320, { label: 'agent.py: summarize', kind: 'function', is_llm: true }), n('end', 'end', 1040, 200, { label: 'End' })],
      edges: [{ id: 'a', source: 'start', target: 'llm' }, { id: 'b', source: 'llm', target: 'cond' }, { id: 'c', source: 'cond', target: 'tool', label: 'order_status' },
        { id: 'd', source: 'cond', target: 'code', label: 'general' }, { id: 'e', source: 'tool', target: 'end' }, { id: 'f', source: 'code', target: 'end' }] }
    const r = await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: wf })
    await page.goto(`/workflows/${(await r.json()).data.id}`); await expect(page.locator('.react-flow__node')).toHaveCount(6)
    await page.waitForTimeout(600); await page.mouse.move(5, 5)
    await page.screenshot({ path: out('node-colors-light') })
    await page.getByRole('button', { name: /dark mode/i }).click(); await page.waitForTimeout(500); await page.mouse.move(5, 5)
    await page.screenshot({ path: out('node-colors-dark') })
    await page.getByRole('button', { name: /light mode|dark mode/i }).click()
  })
})

async function admin(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return apiToken(page)
}
const slow = (n: number, name: string) => {
  const ids = ['s', ...Array.from({ length: n }, (_, i) => `wait${i + 1}`), 'e']
  return { name, state: [{ name: 'message', type: 'string' }, { name: 'out', type: 'string' }],
    nodes: ids.map((id, i) => ({ id, type: i === 0 ? 'start' : i === ids.length - 1 ? 'end' : 'tool', position: { x: 40 + i * 220, y: 180 },
      data: i === 0 ? { label: 'Start' } : i === ids.length - 1 ? { label: 'End' } : { label: `Wait ${i}`, mode: 'function', function: 'sleep_demo', output_field: 'out' } })),
    edges: ids.slice(1).map((id, i) => ({ id: `e${i}`, source: ids[i], target: id })) }
}
async function open(page: Page, token: string | null, wf: object) {
  const r = await page.request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: wf })
  await page.goto(`/workflows/${(await r.json()).data.id}`)
}

test.describe('runtime states', () => {
  test.use({ viewport: { width: 1440, height: 900 } })
  test('capture cancel / timeout / validation', async ({ page }) => {
    const t = await admin(page)
    await open(page, t, slow(4, 'Slow demo (cancel)')); await page.locator('#run-btn').click()
    await expect(page.locator('.trace-row[data-span="wait1#1"]')).toBeVisible(); await page.locator('#cancel-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'cancelled'); await page.mouse.move(5, 5); await page.waitForTimeout(300)
    await page.screenshot({ path: out('runtime-cancelled') })
    await open(page, t, slow(6, 'Slow demo (timeout)')); await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'timeout', { timeout: 15000 }); await page.mouse.move(5, 5); await page.waitForTimeout(300)
    await page.screenshot({ path: out('runtime-timeout') })
    await open(page, t, { name: 'Broken graph', state: [{ name: 'message', type: 'string' }],
      nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
        { id: 'a', type: 'llm', position: { x: 260, y: 80 }, data: { label: 'Draft', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
        { id: 'b', type: 'llm', position: { x: 480, y: 80 }, data: { label: 'Refine', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'message' } },
        { id: 'lonely', type: 'tool', position: { x: 260, y: 300 }, data: { label: 'Unreachable tool', mode: 'function', function: 'lookup_order', output_field: 'message' } },
        { id: 'e', type: 'end', position: { x: 700, y: 150 }, data: { label: 'End' } }],
      edges: [{ id: '1', source: 's', target: 'a' }, { id: '2', source: 'a', target: 'b' }, { id: '3', source: 'b', target: 'a' }, { id: '4', source: 'lonely', target: 'e' }] })
    await page.locator('#run-btn').click(); await page.locator('#run-tab').click()
    await expect(page.locator('#validation-errors')).toBeVisible(); await page.mouse.move(5, 5); await page.waitForTimeout(300)
    await page.screenshot({ path: out('runtime-validation-errors') })
  })
})
