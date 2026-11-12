import { expect, test } from '@playwright/test'
import { vt } from './catalog'
import { login } from './helpers'

test('admin creates a budget and types the target name to delete it', async ({ page }) => {
  const email = `budget${Date.now()}@example.com`
  const registered = await page.request.post('/api/auth/register', { data: { email, password: 'secret12' } })
  expect(registered.ok()).toBeTruthy()
  await login(page)
  await page.goto('/settings/usage')
  const card = page.locator('#usage-budgets')
  await card.getByRole('button', { name: vt('settings.usage.budgets.add') }).click()
  await page.locator('#usage-budget-target').click()
  await page.getByRole('option', { name: email, exact: true }).click()
  await page.locator('#usage-budget-amount').fill('25')
  await card.getByRole('button', { name: vt('common.save'), exact: true }).click()

  const row = card.getByRole('row').filter({ hasText: email })
  await row.getByRole('button', { name: vt('settings.usage.budgets.deleteTitle', { name: email }) }).click()
  const input = page.locator('#usage-budget-delete-input')
  const confirm = page.locator('#usage-budget-delete-submit')
  await input.fill(email.toUpperCase())
  await expect(confirm).toBeDisabled()
  await input.fill(email)
  await expect(confirm).toBeEnabled()
  await confirm.click()
  await expect(row).toHaveCount(0)
})
