import { test, expect } from '@playwright/test'
import { confirmDelete } from './confirm'
// create a workflow token in the UI, trigger a sync run over REST, see it in history as API.
test('api trigger: token, sync run, history source', async ({ page }) => {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  await page.goto('/workflows/example')
  await page.locator('#more-btn').click(); await page.locator('#api-btn').click()
  await page.locator('#api-token-name').fill('e2e'); await page.locator('#api-create').click()
  const token = await page.locator('#api-token-value').inputValue()
  expect(token).toMatch(/^wft_/)
  await expect(page.locator('#api-signing-secret')).toHaveValue(/^whsec_/)  //: shown once with the token
  await expect(page.locator('#api-curl')).toContainText(token)
  await expect(page.locator('[data-testid=api-token-row]', { hasText: 'e2e' }).first()).toBeVisible()
  const r = await page.request.post('/api/hooks/workflows/example/runs', { headers: { Authorization: `Bearer ${token}` }, data: { input: { message: 'where is my order A100' }, mode: 'sync' } })
  const body = await r.json()
  expect(r.status()).toBe(200); expect(body.data.status).toBe('ok'); expect(body.data.final_state.intent).toBe('order_status')
  await page.keyboard.press('Escape')
  await page.reload()
  await page.locator('#history-all').click()
  await expect(page.locator('[data-testid=history-row]').first().locator('[data-testid=history-source]')).toHaveText('API')
  await page.keyboard.press('Escape')
  // revoked tokens are rejected
  await page.locator('#more-btn').click(); await page.locator('#api-btn').click()
  await page.locator('[data-testid=api-token-row]', { hasText: 'e2e' }).first().getByRole('button', { name: /Thu hồi/ }).click()
  await confirmDelete(page, 'e2e')
  const r2 = await page.request.post('/api/hooks/workflows/example/runs', { headers: { Authorization: `Bearer ${token}` }, data: {} })
  expect(r2.status()).toBe(401); expect((await r2.json()).error.code).toBe('TRIGGER_TOKEN_INVALID')
  // revoked tokens are hidden until "Show revoked" is switched on; the dialog fits the viewport with its tabs visible
  const revokedRows = page.locator('[data-testid=api-token-row]', { hasText: 'đã thu hồi' })
  await expect(revokedRows).toHaveCount(0)
  const toggle = page.locator('#api-show-revoked'); await expect(toggle).toHaveAttribute('data-state', 'unchecked')
  await toggle.click(); await expect(revokedRows.first()).toBeVisible()
  const box = (await page.locator('#api-dialog').boundingBox())!; const vh = page.viewportSize()!.height
  expect(box.y).toBeGreaterThanOrEqual(0); expect(box.y + box.height).toBeLessThanOrEqual(vh)
  await expect(page.locator('#api-deliveries-tab')).toBeInViewport()
  await toggle.click(); await expect(revokedRows).toHaveCount(0)
})
