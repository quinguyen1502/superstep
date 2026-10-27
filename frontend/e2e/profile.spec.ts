import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// TASK-0052: the Profile section shows the account; changing the password needs the current one, keeps this
// browser signed in and signs out every other session of the account.
const uid = () => Math.random().toString(36).slice(2, 10)
async function register(page: Page, email: string) {
  await page.goto('/register'); await page.getByLabel('Email').fill(email); await page.getByLabel('Mật khẩu', { exact: true }).fill('goodpass1')
  await page.getByLabel('Xác nhận mật khẩu').fill('goodpass1'); await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
}

test('profile: account details, then a password change that signs out the other session', async ({ page, browser }) => {
  const email = `profile-${uid()}@example.com`
  await register(page, email)
  const other = await browser.newContext(); const op = await other.newPage()
  await op.goto('/login'); await op.getByLabel('Email').fill(email); await op.getByLabel('Mật khẩu', { exact: true }).fill('goodpass1')
  await op.locator('#auth-submit').click(); await expect(op).toHaveURL(/\/workflows$/)

  await page.locator('#user-menu').click(); await page.locator('#profile-item').click()
  await expect(page).toHaveURL(/\/settings\/profile$/)
  await expect(page.locator('#profile-email')).toHaveText(email)
  await expect(page.locator('#profile-role')).toHaveText('Người chỉnh sửa')
  await expect(page.locator('#profile-created')).not.toHaveText('—')
  await page.locator('#profile-notify').click(); await expect(page.locator('#notify-settings-dialog')).toBeVisible(); await page.keyboard.press('Escape')

  const save = page.locator('#password-save')
  await page.locator('#current-password').fill('wrongpass1'); await page.locator('#new-password').fill('newpass22')
  await page.locator('#new-confirm').fill('newpass2'); await expect(save).toBeDisabled()  // confirm does not match
  await page.locator('#new-confirm').fill('newpass22'); await save.click()
  await expect(page.locator('#password-error')).toHaveText('Mật khẩu hiện tại không đúng')

  await page.waitForTimeout(1100)  // tokens carry whole seconds; the other session must be from an earlier second than the change
  await page.locator('#current-password').fill('goodpass1'); await save.click()
  await expect(page.locator('#password-changed')).toBeVisible()
  await expect(page.locator('#current-password')).toHaveValue('')

  await page.reload(); await expect(page.locator('#profile-email')).toHaveText(email)  // this browser stays signed in
  await op.goto('/workflows').catch(() => {}); await expect(op).toHaveURL(/\/login\?expired=1/)
  expect(await apiToken(page, email, 'newpass22')).toBeTruthy()
  await other.close()
})

test('profile of a read-only account (the public demo visitor): language local, password and notifications locked', async ({ page }) => {
  await register(page, `readonly-${uid()}@example.com`)
  // what GET /api/me says for the demo visitor (STUDIO_DEMO_MODE is off in these tests)
  await page.route(u => u.pathname === '/api/me', async r => { const res = await r.fetch(); const body = await res.json(); body.data.read_only = true; await r.fulfill({ response: res, json: body }) })
  const prefWrites: string[] = []; page.on('request', r => { if (r.method() === 'PUT' && r.url().includes('/api/notifications/preferences')) prefWrites.push(r.url()) })
  await page.goto('/settings/profile')
  await expect(page.locator('#password-read-only')).toBeVisible()
  await expect(page.locator('#current-password')).toBeDisabled(); await expect(page.locator('#password-save')).toBeDisabled()
  await page.locator('#profile-lang').click(); await page.getByRole('option', { name: 'English' }).click()
  await expect(page.locator('#profile-notify')).toHaveText('Manage')  // the UI language still changes, in this browser
  await page.locator('#profile-notify').click()
  await expect(page.locator('#notify-read-only')).toBeVisible(); await expect(page.locator('#notify-pref-in_app')).toBeDisabled()
  expect(prefWrites).toEqual([])  // nothing the server would refuse
})
