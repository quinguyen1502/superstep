import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// TASK-0014: share a workflow from the editor, the viewer gets a read-only editor, the admin manages roles in Settings → Users.
async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login'); await page.getByLabel('Email').fill(email); await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page, email, password)}` }
}
const WF = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }],
  nodes: [{ id: 'start', type: 'start', position: { x: 60, y: 120 }, data: { label: 'Start' } }, { id: 'end', type: 'end', position: { x: 360, y: 120 }, data: { label: 'End' } }],
  edges: [{ id: 'e1', source: 'start', target: 'end' }] })

test('share as viewer, read-only editor, admin changes the role and deactivates', async ({ page, browser }) => {
  const email = `viewer${Date.now()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  const auth = await login(page); const name = `Shared ${Date.now()}`
  const wid = (await (await page.request.post('/api/workflows', { headers: auth, data: WF(name) })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  await page.locator('#more-btn').click(); await page.locator('#share-btn').click(); await page.locator('#share-email').fill(email); await page.locator('#share-add').click()
  await expect(page.locator('#share-list')).toContainText(email); await expect(page.locator('#share-list')).toContainText('Chủ sở hữu')
  await page.keyboard.press('Escape')

  const ctx = await browser.newContext(); const other = await ctx.newPage()
  await login(other, email, 'secret12')
  const row = other.getByRole('row', { name: new RegExp(name) })
  await expect(row.locator('.wf-shared')).toContainText('admin@example.com'); await expect(row.locator('.wf-access')).toContainText('Chỉ xem')
  await row.click(); await expect(other.locator('#view-only')).toBeVisible(); await expect(other.locator('#save-btn')).toBeDisabled()
  await other.locator('#run-btn').click(); await expect(other.getByText('Hoàn thành').first()).toBeVisible({ timeout: 15000 })

  await page.goto('/settings/users')
  const user = page.locator(`.user-row[data-email="${email}"]`)
  await user.getByRole('combobox').click(); await page.getByRole('option', { name: 'Người xem' }).click()
  await expect(user.getByRole('combobox')).toContainText('Người xem')
  // a global viewer creates no knowledge bases or MCP servers: no Knowledge tab, no Add button, an old link goes to Profile
  await other.goto('/settings/mcp'); await expect(other.locator('#mcp-sandbox-note')).toBeVisible()
  await expect(other.locator('#mcp-add')).toHaveCount(0); await expect(other.locator('#settings-nav-knowledge')).toHaveCount(0)
  await other.goto('/settings/knowledge'); await expect(other).toHaveURL(/\/settings\/profile$/)
  await expect(page.locator('#roles-matrix')).toContainText('users.manage')
  await user.getByRole('switch').click(); await expect(user).toContainText('Đã vô hiệu hoá')
  await other.reload(); await expect(other).toHaveURL(/\/login/)
  await ctx.close()
})
