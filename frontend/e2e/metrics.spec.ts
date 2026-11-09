import { test, expect } from '@playwright/test'
// per-run metrics in the live timeline and in history (mock mode: estimated tokens, $0, no trace link).
test('run metrics: tokens, cost and history', async ({ page }) => {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  await page.goto('/workflows/example'); await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  await expect(page.locator('#trace-tokens')).toContainText('token')
  await expect(page.locator('#trace-cost')).toHaveText('$0')
  await expect(page.locator('#trace-link')).toHaveCount(0) // no exporter / STUDIO_TRACE_URL configured
  await expect(page.locator('[data-testid=span-tokens]').first()).toBeVisible()
  await page.locator('#history-all').click()
  const row = page.locator('[data-testid=history-row]').first()
  await expect(row.locator('[data-testid=history-tokens]')).toContainText('token')
  await expect(row.locator('[data-testid=history-cost]')).toHaveText('$0')
  await row.click(); await expect(page.locator('#trace-cost')).toHaveText('$0') // replay shows the stored metrics
})
