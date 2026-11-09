import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import { vt, vtHead } from './catalog'
// the session is an HttpOnly cookie, failed sign-ins lock an e-mail, an admin reset link sets a new password
// and signs out the old session, and logout ends the session on the server too.
const uid = () => Math.random().toString(36).slice(2, 10)
async function signInForm(page: Page, email: string, password: string) {
  await page.goto('/login'); await page.getByLabel('Email').fill(email); await page.getByLabel(vt('auth.password'), { exact: true }).fill(password)
  await page.locator('#auth-submit').click()
}

test('session cookie is not readable by the page, and logout ends it', async ({ page }) => {
  await signInForm(page, 'admin@example.com', 'admin123'); await expect(page).toHaveURL(/\/workflows$/)
  expect(await page.evaluate(() => [document.cookie.includes('studio_session'), localStorage.getItem('token')])).toEqual([false, null])
  const cookie = (await page.context().cookies()).find(c => c.name === 'studio_session')
  expect(cookie?.httpOnly).toBe(true); expect(cookie?.sameSite).toBe('Lax')
  await page.locator('#user-menu').click(); await page.getByRole('menuitem', { name: vt('common.logout') }).click()
  await expect(page).toHaveURL(/\/login$/)
  expect((await page.request.get('/api/me')).status()).toBe(401)
})

test('five wrong passwords lock the e-mail, even for the right password', async ({ page }) => {
  const email = `lock-${uid()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'goodpass1' } })).ok()).toBeTruthy()
  await page.context().clearCookies()
  for (let i = 0; i < 4; i++) {
    await signInForm(page, email, 'wrongpass1'); await expect(page.locator('#auth-error')).toHaveText(vt('errors.AUTH_INVALID_CREDENTIALS'))
  }
  await signInForm(page, email, 'wrongpass1'); await expect(page.locator('#auth-error')).toContainText(vtHead('errors.AUTH_LOCKED'))
  await signInForm(page, email, 'goodpass1'); await expect(page.locator('#auth-error')).toContainText(vtHead('errors.AUTH_LOCKED'))
})

test('admin reset link: new password, old session signed out', async ({ page, browser }) => {
  const email = `reset-${uid()}@example.com`
  const user = await browser.newContext(); const up = await user.newPage()
  await up.goto('/register'); await up.getByLabel('Email').fill(email); await up.getByLabel(vt('auth.password'), { exact: true }).fill('goodpass1')
  await up.getByLabel(vt('auth.confirm')).fill('goodpass1'); await up.locator('#auth-submit').click(); await expect(up).toHaveURL(/\/workflows$/)

  // no SMTP in this setup: "forgot password" says to ask an admin
  const anon = await browser.newPage(); await anon.goto('/login'); await anon.locator('#forgot-link').click()
  await expect(anon.getByText(vt('reset.askAdmin'))).toBeVisible(); await anon.close()

  await signInForm(page, 'admin@example.com', 'admin123'); await expect(page).toHaveURL(/\/workflows$/)
  await page.goto('/settings/users')
  await page.locator(`.user-row[data-email="${email}"] .user-reset`).click()
  const link = await page.locator('#reset-link').inputValue(); expect(link).toContain('/reset-password?token=')
  await page.waitForTimeout(1100)  // tokens carry whole seconds; the old one must be from an earlier second than the change

  const fresh = await browser.newPage(); await fresh.goto(link)
  await fresh.locator('#new-password').fill('newpass12'); await fresh.locator('#new-confirm').fill('newpass12'); await fresh.locator('#reset-submit').click()
  await expect(fresh).toHaveURL(/\/login\?reset=1/); await expect(fresh.locator('#reset-notice')).toBeVisible()
  await expect(fresh.getByLabel('Email')).toHaveValue(email)
  await fresh.getByLabel(vt('auth.password'), { exact: true }).fill('newpass12'); await fresh.locator('#auth-submit').click(); await expect(fresh).toHaveURL(/\/workflows$/)

  // the link works once, and the user's earlier session is gone
  await fresh.goto(link); await fresh.locator('#new-password').fill('other1234'); await fresh.locator('#new-confirm').fill('other1234'); await fresh.locator('#reset-submit').click()
  await expect(fresh.locator('#reset-error')).toContainText(vt('errors.PASSWORD_RESET_INVALID'))
  await up.goto('/workflows').catch(() => {}); await expect(up).toHaveURL(/\/login\?expired=1/)
  expect(await apiToken(page, email, 'newpass12')).toBeTruthy()
  await user.close()
})
