import { test, expect, type Page } from '@playwright/test'
import { confirmDelete } from './confirm'
import { signIn } from './helpers'

const uid = () => Math.random().toString(36).slice(2, 8)
async function register(page: Page, email: string, pw = 'goodpass1') {
  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(pw)
  await page.getByLabel('Xác nhận mật khẩu').fill(pw)
  await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
}
async function login(page: Page, email: string, pw: string) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(pw)
  await page.getByLabel('Mật khẩu', { exact: true }).press('Enter')
}

test('register → logout → login → list → open example → run → done', async ({ page }) => {
  const email = `e2e-${uid()}@example.com`
  await page.goto('/register')
  await page.getByLabel('Mật khẩu', { exact: true }).fill('weak')
  await expect(page.locator('#pw-rules')).toContainText('Ít nhất 8 ký tự')
  await expect(page.locator('#auth-submit')).toBeDisabled()
  await register(page, email)
  await page.locator('#user-menu').click(); await page.getByText('Đăng xuất').click()
  await expect(page).toHaveURL(/\/login/)
  await login(page, email, 'goodpass1')
  await expect(page).toHaveURL(/\/workflows$/)
  await page.getByRole('cell', { name: /Customer support/i }).first().click()
  await expect(page).toHaveURL(/\/workflows\/\w+$/)
  const wid = page.url().split('/').pop()!
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await page.locator('#back-btn').click()
  // this workflow's row shows the run as its last run. Each row has the status twice: a phone line (sm:hidden) before the
  // Last run column, so "the first ok on the page" was the hidden copy (TASK-0196).
  const row = page.getByRole('row').filter({ hasText: wid })
  await expect(row.getByText('ok', { exact: true }).filter({ visible: true })).toHaveCount(1)
})

test('wrong password shows a generic error', async ({ page }) => {
  const email = `e2e-${uid()}@example.com`
  await register(page, email)
  await page.evaluate(() => localStorage.clear()); await page.context().clearCookies()  // sign out: the session is a cookie (TASK-0045)
  // the app may itself redirect to /login once the token is gone (a header poll gets 401), racing this goto
  await page.goto('/login').catch(() => {}); await expect(page).toHaveURL(/\/login/); await page.waitForLoadState()
  await login(page, email, 'wrongpass1')
  await expect(page.locator('#auth-error')).toHaveText('Sai email hoặc mật khẩu')
  await login(page, `nobody-${email}`, 'wrongpass1')
  await expect(page.locator('#auth-error')).toHaveText('Sai email hoặc mật khẩu')
  await login(page, email, 'goodpass1')
  await expect(page).toHaveURL(/\/workflows$/)
})

test('expired token redirects to login with notice and returns to original page', async ({ page }) => {
  await page.goto('/login'); await login(page, 'admin@example.com', 'admin123')
  await expect(page).toHaveURL(/\/workflows$/); await page.waitForLoadState("networkidle") // list + pending-runs requests done before the token is swapped
  await page.evaluate(() => localStorage.setItem('session_exp', String(Math.floor(Date.now() / 1000) - 60)))  // the session ran out
  await page.goto('/workflows/example')
  await expect(page).toHaveURL(/\/login\?expired=1&next=%2Fworkflows%2Fexample/)
  await expect(page.locator('#expired-notice')).toBeVisible()
  await login(page, 'admin@example.com', 'admin123')
  await expect(page).toHaveURL(/\/workflows\/example$/)
  // server-side rejection (bad signature, not expired client-side) also redirects
  await page.context().addCookies([{ name: 'studio_session', value: 'not.a.jwt', domain: new URL(page.url()).hostname, path: '/' }])  // the page thinks it is signed in
  await page.goto('/workflows').catch(() => {}) // app redirects mid-navigation on 401
  await expect(page).toHaveURL(/\/login\?expired=1/)
  await expect(page.locator('#expired-notice')).toBeVisible()
})

test('list: rename / duplicate / delete with confirm, edge cases, not-found', async ({ page }) => {
  await register(page, `e2e-${uid()}@example.com`)
  const rows = page.locator('tbody tr')
  await expect(rows).toHaveCount(1)
  const openMenu = async (i: number, item: string) => {
    await expect(page.locator('[role=menu]')).toHaveCount(0)
    await page.locator('.wf-actions').nth(i).click()
    await page.getByRole('menuitem', { name: item, exact: true }).click()
  }
  // rename: empty rejected, long name truncated in list
  await openMenu(0, 'Đổi tên')
  await page.locator('#rename-input').fill('   ')
  await expect(page.locator('#rename-save')).toBeDisabled()
  await expect(page.locator('#rename-error')).toHaveText('Tên không được để trống')
  const long = 'Very long workflow name '.repeat(5).trim().slice(0, 100)
  await page.locator('#rename-input').fill(long); await page.locator('#rename-save').click()
  await expect(page.getByText(long, { exact: true })).toBeVisible()  // the full name is the text (tooltip on hover)
  // duplicate naming
  await openMenu(0, 'Nhân bản')
  await expect(page.locator('#wf-notice')).toContainText('(copy)')
  await expect(rows).toHaveCount(2)
  // rename to duplicate name rejected
  const orig = rows.filter({ has: page.getByText(long, { exact: true }) }).locator('.wf-actions')
  await expect(page.locator('[role=menu]')).toHaveCount(0); await orig.click(); await page.getByRole('menuitem', { name: 'Đổi tên', exact: true }).click()
  await page.locator('#rename-input').fill(`${long} (copy)`); await page.locator('#rename-save').click()
  await expect(page.locator('#rename-error')).toHaveText('Đã có workflow trùng tên')
  await page.keyboard.press('Escape')
  // search no results
  await page.locator('#wf-search').fill('zzz-nothing')
  await expect(page.locator('#wf-no-results')).toBeVisible()
  await page.getByRole('button', { name: 'Xoá tìm kiếm' }).first().click()
  await expect(rows).toHaveCount(2)
  // remember an id, delete both (cancel once), then empty state
  const firstId = (await rows.first().locator('.font-mono').textContent())!
  await openMenu(0, 'Xoá')
  await page.getByRole('button', { name: 'Huỷ' }).click(); await expect(rows).toHaveCount(2)
  for (let i = 0; i < 2; i++) {
    await openMenu(0, 'Xoá'); await confirmDelete(page)
    await expect(page.locator('[role=dialog], [role=alertdialog]')).toHaveCount(0)
  }
  await expect(page.locator('#wf-empty')).toBeVisible()
  // deleted and foreign workflow URLs show not-found
  await page.goto(`/workflows/${firstId}`)
  await expect(page.locator('#editor-not-found')).toContainText('Không tìm thấy workflow')
  await page.goto('/workflows/example')
  await expect(page.locator('#editor-not-found')).toBeVisible()
  await page.locator('#back-to-list').click(); await expect(page).toHaveURL(/\/workflows$/)
})

test('100+ workflows render and filter quickly', async ({ page, request }) => {
  const email = `e2e-${uid()}@example.com`
  const r = await request.post('/api/auth/register', { data: { email, password: 'goodpass1' } })
  const { token } = (await r.json()).data
  await Promise.all(Array.from({ length: 110 }, (_, i) => request.post('/api/workflows', { headers: { Authorization: `Bearer ${token}` }, data: { name: `Bulk ${String(i).padStart(3, '0')}`, nodes: [], edges: [] } })))
  await page.goto('/login'); await signIn(page, email, 'goodpass1')
  await page.goto('/workflows')
  await expect(page.locator('tbody tr')).toHaveCount(111)
  const t0 = Date.now(); await page.locator('#wf-search').fill('Bulk 10')
  await expect(page.locator('tbody tr')).toHaveCount(10)
  expect(Date.now() - t0).toBeLessThan(1500)
})
