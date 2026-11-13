import { expect, type Page } from '@playwright/test'
/** The shared ConfirmDeleteDialog: the button stays disabled until the exact name is typed (UI rule). */
export async function confirmDelete(page: Page, name?: string) {
  const dialog = page.locator('#confirm-delete'); await expect(dialog).toBeVisible()
  const submit = page.locator('#confirm-delete-submit'); await expect(submit).toBeDisabled()
  const n = name ?? (await dialog.locator('[data-confirm-name]').textContent())!
  const input = page.locator('#confirm-delete-input')
  await input.fill(n.slice(0, -1) || 'x'); await expect(submit).toBeDisabled()
  await input.fill(n); await expect(submit).toBeEnabled(); await submit.click()
  await expect(dialog).toHaveCount(0)
}
