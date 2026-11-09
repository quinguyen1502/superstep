import { test, expect } from '@playwright/test'
import { apiToken } from './helpers'
// save creates versions, diff two versions, restore an old one, history shows the version that ran.
test('versions: save, diff, restore, run tagged with version', async ({ page }) => {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  const H = { Authorization: `Bearer ${await apiToken(page)}` }
  const wid = (await (await page.request.post('/api/workflows/example/duplicate', { headers: H })).json()).data.id
  try {
    await page.goto(`/workflows/${wid}`)
    const nameInput = page.locator('header input').first()
    await nameInput.fill(`Versioned ${Date.now()}`)
    await page.getByRole('button', { name: 'Lưu', exact: true }).click()
    await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/versions`, { headers: H })).json()).data.total).toBe(2)
    // a graph change (v3): drop the last node's edges + node through the API, then reload
    const wf = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
    const gone = wf.nodes[wf.nodes.length - 1].id
    await page.request.post('/api/workflows', { headers: H, data: { ...wf, nodes: wf.nodes.slice(0, -1), edges: wf.edges.filter((e: any) => e.source !== gone && e.target !== gone) } })
    await page.reload()
    await nameInput.fill(`Unsaved ${Date.now()}`)  // unsaved edit: the restore confirm must warn
    await page.locator('#more-btn').click(); await page.locator('#versions-btn').click()
    await expect(page.locator('[data-testid=version-row]')).toHaveCount(3)
    await expect(page.locator('#version-diff')).toContainText(gone)  // default compare: v2 → v3
    await page.locator('[data-testid=version-row]', { hasText: 'v1' }).locator('[data-testid=restore-btn]').click()
    await expect(page.locator('[data-testid=restore-unsaved-warning]')).toBeVisible()
    await page.locator('[data-testid=restore-confirm]').click()
    await expect(page.locator('[data-testid=version-row]')).toHaveCount(4)
    await expect(page.locator('[data-testid=version-row]').first()).toContainText('Khôi phục từ v1')
    await page.keyboard.press('Escape')
    await expect(page.locator('.react-flow__node', { hasText: gone })).toHaveCount(1)  // editor shows the restored graph
    await page.locator('#run-btn').click()
    await page.locator('#history-all').click()
    await expect(page.locator('[data-testid=history-row]').first().locator('[data-testid=history-version]')).toHaveText('v4')
    await page.keyboard.press('Escape')
    // restoring v1 again is a no-op (v4 already has its content): the dialog says so, no v5
    await page.locator('#more-btn').click(); await page.locator('#versions-btn').click()
    await page.locator('[data-testid=version-row]', { hasText: 'v1' }).locator('[data-testid=restore-btn]').click()
    await expect(page.locator('[data-testid=restore-unsaved-warning]')).toHaveCount(0)
    await page.locator('[data-testid=restore-confirm]').click()
    await expect(page.locator('#versions-notice')).toContainText('giống hệt')
    await expect(page.locator('[data-testid=version-row]')).toHaveCount(4)
  } finally {
    await page.request.delete(`/api/workflows/${wid}`, { headers: H })
  }
})
