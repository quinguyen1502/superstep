import { test, expect } from '@playwright/test'
import { login, SIMPLE } from './helpers'
import { vt } from './catalog'
// Settings → Usage: an admin sees runs and cost for a window and the top workflows; a member without users.manage sees no Usage entry.

test('admin reads usage; a member has no Usage section', async ({ page, browser }) => {
  const email = `usage${Date.now()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  const H = await login(page); const name = `Usage wf ${Date.now()}`
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: SIMPLE(name) })).json()).data.id
  await page.goto(`/workflows/${wid}`); await page.locator('#run-btn').click()
  await expect(page.getByText(vt('trace.ok')).first()).toBeVisible({ timeout: 15000 })

  await page.goto('/settings/usage')
  await expect(page.locator('#settings-nav-usage')).toBeVisible()
  await expect(page.locator('#usage-runs-value')).not.toHaveText('0')
  await expect(page.locator('#usage-workflows-table')).toContainText(name)
  await expect(page.locator('#usage-health')).toContainText(vt('settings.usage.health.title'))
  await page.locator('#usage-window').click(); await page.getByRole('option', { name: vt('settings.usage.windows.24h') }).click()
  await expect(page.locator('#usage-window')).toContainText(vt('settings.usage.windows.24h'))
  await expect(page.locator('#usage-workflows-table')).toContainText(name)

  const ctx = await browser.newContext(); const other = await ctx.newPage()
  await login(other, email, 'secret12')
  await other.goto('/settings/profile'); await expect(other.locator('#settings-nav-profile')).toBeVisible()
  await expect(other.locator('#settings-nav-usage')).toHaveCount(0)
  await other.goto('/settings/usage'); await expect(other).toHaveURL(/\/settings\/profile$/)  // like other admin sections
  expect((await other.request.get('/api/admin/usage')).status()).toBe(403)
  await ctx.close()
})
