import { test, expect } from '@playwright/test'
import { login, SIMPLE } from './helpers'
import { vt } from './catalog'
// Settings → Usage: an admin sees runs and cost for a window, the top workflows, models, users and teams; a member without users.manage sees no Usage entry.

test('admin reads usage; a member has no Usage section', async ({ page, browser }) => {
  const email = `usage${Date.now()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  const H = await login(page); const name = `Usage wf ${Date.now()}`
  const before = (await (await page.request.get('/api/admin/usage?window=24h', { headers: H })).json()).data
  const prior = before.totals.runs
  if (!before.models.length) {  // a fresh database: the Models table shows its empty state and when per-model data starts
    await page.goto('/settings/usage')
    await expect(page.locator('#usage-models-empty')).toHaveText(vt('settings.usage.models.empty'))
    await expect(page.locator('#usage-models-since')).toHaveText(vt('settings.usage.models.notYet'))
  }
  const wid = (await (await page.request.post('/api/workflows', { headers: H, data: SIMPLE(name) })).json()).data.id
  await page.goto(`/workflows/${wid}`); await page.locator('#run-btn').click()
  await expect(page.getByText(vt('trace.ok')).first()).toBeVisible({ timeout: 15000 })

  await page.goto('/settings/usage')
  await expect(page.locator('#settings-nav-usage')).toBeVisible()
  await expect(page.locator('#usage-runs-value')).not.toHaveText('0')
  await expect(page.locator('#usage-workflows-table')).toBeVisible()
  await expect(page.locator('#usage-health')).toContainText(vt('settings.usage.health.title'))
  const usage = (await (await page.request.get('/api/admin/usage?window=24h', { headers: H })).json()).data
  expect(usage.totals.runs).toBeGreaterThanOrEqual(prior + 1)
  // The table lists the top 10 by runs or cost; other e2e workflows in this studio can outrank a single new run.
  const listed = usage.top_workflows.some((w: { name?: string }) => w.name === name)
  if (listed) await expect(page.locator('#usage-workflows-table')).toContainText(name)
  // Models: one row per model in the API answer, sorted by the chosen column (only names the API returns are asserted)
  await expect(page.locator('#usage-models-table')).toBeVisible()
  await expect(page.locator('[data-testid="usage-model-row"]')).toHaveCount(usage.models.length)
  if (usage.models.length) {
    type M = { model: string; calls: number; tokens_in: number; tokens_out: number }
    const top = [...usage.models].sort((a: M, b: M) => b.calls - a.calls || a.model.localeCompare(b.model))[0]
    await page.locator('#usage-models-sort').click(); await page.getByRole('option', { name: vt('settings.usage.models.sort.calls') }).click()
    await expect(page.locator('[data-testid="usage-model-row"]').first()).toContainText(top.model)
  }
  // Users and teams: SQL tables for admins (never metric labels)
  await expect(page.locator('#usage-users-table')).toBeVisible(); await expect(page.locator('#usage-teams-table')).toBeVisible()
  await expect(page.locator('[data-testid="usage-user-row"]')).toHaveCount(usage.users.length)
  if (usage.users.length) await expect(page.locator('[data-testid="usage-users-total"]')).toContainText(vt('settings.usage.people.total'))
  await expect(page.locator('#usage-health-channels')).toContainText(vt('settings.usage.health.channels'))
  await page.locator('#usage-window').click(); await page.getByRole('option', { name: vt('settings.usage.windows.24h') }).click()
  await expect(page.locator('#usage-window')).toContainText(vt('settings.usage.windows.24h'))
  if (listed) await expect(page.locator('#usage-workflows-table')).toContainText(name)

  const ctx = await browser.newContext(); const other = await ctx.newPage()
  await login(other, email, 'secret12')
  await other.goto('/settings/profile'); await expect(other.locator('#settings-nav-profile')).toBeVisible()
  await expect(other.locator('#settings-nav-usage')).toHaveCount(0)
  await other.goto('/settings/usage'); await expect(other).toHaveURL(/\/settings\/profile$/)  // like other admin sections
  expect((await other.request.get('/api/admin/usage')).status()).toBe(403)
  await expect(other.locator('#usage-users-table')).toHaveCount(0); await expect(other.locator('#usage-teams-table')).toHaveCount(0)
  await ctx.close()
})
