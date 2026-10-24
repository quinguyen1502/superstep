import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
import { confirmDelete } from './confirm'
// TASK-0029: teams + team share, ownership transfer, activity log, delete user with reassignment, org-resource policy, dependents on delete.
async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login'); await page.getByLabel('Email').fill(email); await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page, email, password)}` }
}
const N = (id: string, type: string, x: number, data: Record<string, unknown> = {}) => ({ id, type, position: { x, y: 120 }, data: { label: id, ...data } })
const WF = (name: string, mid: ReturnType<typeof N>[] = []) => ({ name, state: [{ name: 'message', type: 'string' }],
  nodes: [N('start', 'start', 60), ...mid, N('end', 'end', 600)],
  edges: mid.length ? [{ id: 'e1', source: 'start', target: mid[0].id }, { id: 'e2', source: mid[0].id, target: 'end' }] : [{ id: 'e1', source: 'start', target: 'end' }] })
async function register(page: Page, prefix: string) {
  const email = `${prefix}${Date.now()}@example.com`
  expect((await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })).ok()).toBeTruthy()
  return email
}

test('team share, transfer, activity log and delete user with reassignment', async ({ page, browser }) => {
  const member = await register(page, 'member'); const heir = await register(page, 'heir')
  const auth = await login(page); const stamp = Date.now()
  // team with a member
  await page.goto('/settings/teams'); await page.locator('#team-new-name').fill(`Ops ${stamp}`); await page.locator('#team-create').click()
  const card = page.locator('[data-testid^="team-card-"]', { hasText: `Ops ${stamp}` })
  await card.getByLabel('Email thành viên').fill(member); await card.getByRole('button', { name: 'Thêm' }).click()
  await expect(card).toContainText(member)
  // share a workflow with the team from the editor
  const name = `Team wf ${stamp}`
  const wid = (await (await page.request.post('/api/workflows', { headers: auth, data: WF(name) })).json()).data.id
  await page.goto(`/workflows/${wid}`); await page.locator('#more-btn').click(); await page.locator('#share-btn').click()
  await page.locator('#share-kind').click(); await page.getByRole('option', { name: 'Nhóm' }).click()
  await page.locator('#share-team').click(); await page.getByRole('option', { name: new RegExp(`Ops ${stamp}`) }).click()
  await page.locator('#share-add').click(); await expect(page.locator('#share-list')).toContainText(`Ops ${stamp}`)
  // member sees it through the team
  const ctx = await browser.newContext(); const other = await ctx.newPage(); await login(other, member, 'secret12')
  await expect(other.getByRole('row', { name: new RegExp(name) })).toBeVisible(); await ctx.close()
  // transfer ownership to heir from the share dialog
  await page.locator('#transfer-btn').click(); await page.locator('#transfer-email').fill(heir); await page.locator('#transfer-check').click()
  await expect(page.locator('#transfer-clean')).toBeVisible(); await page.locator('#transfer-submit').click()
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/shares`, { headers: auth })).json()).data.owner?.email ?? '').toBe(heir)
  // activity log shows team, share and transfer entries; filter by category
  await page.goto('/settings/activity'); await expect(page.locator('#activity-table')).toContainText(`Ops ${stamp}`)
  await expect(page.locator('#activity-table')).toContainText('Chuyển quyền sở hữu')
  // delete heir: owns a workflow, must reassign back to admin
  await page.goto('/settings/users'); const row = page.locator(`.user-row[data-email="${heir}"]`)
  await row.getByRole('button', { name: `Xoá ${heir}` }).click()
  await page.locator('#delete-reassign').fill('admin@example.com'); await confirmDelete(page, heir)
  await expect(page.locator('#users-notice')).toContainText(heir); await expect(row).toHaveCount(0)
  const w = await (await page.request.get(`/api/workflows/${wid}`, { headers: auth })).json(); expect(w.data.id).toBe(wid)
  // remove the member, stop the team share, then delete the team — each asks for the name
  await page.goto('/settings/teams'); await card.getByRole('button', { name: `Gỡ ${member}` }).click(); await confirmDelete(page, member)
  await expect(card).not.toContainText(member)
  await page.goto(`/workflows/${wid}`); await page.locator('#more-btn').click(); await page.locator('#share-btn').click()
  await page.locator('#share-list').getByRole('button', { name: `Ngừng chia sẻ với Ops ${stamp}` }).click(); await confirmDelete(page, `Ops ${stamp}`)
  await expect(page.locator('#share-list')).not.toContainText(`Ops ${stamp}`); await page.keyboard.press('Escape')
  await page.goto('/settings/teams'); await card.getByRole('button', { name: `Xoá nhóm Ops ${stamp}` }).click(); await confirmDelete(page, `Ops ${stamp}`)
  await expect(card).toHaveCount(0)
})

test('LangSmith card: off and locked until LANGSMITH_API_KEY is set', async ({ page }) => {
  const auth = await login(page)
  const st = (await (await page.request.get('/api/admin/langsmith', { headers: auth })).json()).data
  expect(st).toMatchObject({ configured: false, evals: false })
  await page.goto('/settings/users'); await expect(page.locator('#langsmith-settings')).toBeVisible()
  await expect(page.locator('#langsmith-evals')).toBeDisabled(); await expect(page.locator('#langsmith-not-configured')).toBeVisible()
  const r = await (await page.request.put('/api/admin/langsmith', { headers: auth, data: { evals: true } })).json()
  expect(r.data.evals).toBe(true)  // saved even without a key; nothing is sent until one is set
  await page.request.put('/api/admin/langsmith', { headers: auth, data: { evals: false } })
})

test('org-resource policy and delete warning with dependents', async ({ page }) => {
  const auth = await login(page)
  const pol = await (await page.request.get('/api/admin/policy', { headers: auth })).json()
  expect(pol.data.org_resources_roles.sort()).toEqual(['admin', 'editor'])
  await page.goto('/settings/users'); await expect(page.locator('#org-policy')).toBeVisible()
  const viewer = page.locator('#policy-viewer'); await viewer.click()
  await expect.poll(async () => (await (await page.request.get('/api/admin/policy', { headers: auth })).json()).data.org_resources_roles).toContain('viewer')
  await viewer.click()
  await expect.poll(async () => (await (await page.request.get('/api/admin/policy', { headers: auth })).json()).data.org_resources_roles).not.toContain('viewer')
  // child used by a parent: delete is blocked with the dependents list, then forced
  const stamp = Date.now()
  const child = (await (await page.request.post('/api/workflows', { headers: auth, data: WF(`Child ${stamp}`) })).json()).data.id
  await page.request.post('/api/workflows', { headers: auth, data: WF(`Parent ${stamp}`, [N('sub', 'subgraph', 300, { workflow_id: child })]) })
  await page.goto('/workflows'); await page.locator('#wf-search').fill(`Child ${stamp}`)
  const row = page.getByRole('row', { name: new RegExp(`Child ${stamp}`) })
  await row.getByRole('button').last().click(); await page.getByRole('menuitem', { name: 'Xoá' }).click()
  await expect(page.locator('#delete-dependents')).toContainText(`Parent ${stamp}`)
  await confirmDelete(page, `Child ${stamp}`); await expect(page.locator('#wf-no-results')).toBeVisible()
})
