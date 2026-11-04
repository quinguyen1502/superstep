import { test, expect, type Page } from '@playwright/test'
import { confirmDelete } from './confirm'

// Fake provider servers live in backend/tests/fixtures/mock_chat_api.py (TASK-0030).
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`

async function loginAdmin(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
}
async function chooseProvider(page: Page, label: string) {
  await page.locator('#cred-provider').click(); await page.getByRole('option', { name: label }).click()
}

test('llm providers: test connection, OpenRouter key, Ollama models on the LLM node, run, delete', async ({ page }) => {
  const name = `ollama-${Date.now()}`
  await loginAdmin(page)
  await page.locator('#creds-btn').click()
  const dlg = page.getByRole('dialog')

  // OpenRouter: key required (buttons disabled), header fields, wrong key → PROVIDER_AUTH_FAILED (translated)
  await chooseProvider(page, 'OpenRouter')
  await expect(dlg.locator('#cred-add')).toBeDisabled(); await expect(dlg.locator('#cred-test')).toBeDisabled()
  await expect(dlg.locator('#cred-h-X-Title')).toBeVisible()
  await dlg.locator('#cred-base').fill(`${CHAT}/openrouter/api/v1`); await dlg.locator('#cred-key').fill('sk-or-bad')
  await dlg.locator('#cred-test').click()
  await expect(dlg.locator('#cred-test-result')).toContainText('từ chối API key')
  await dlg.locator('#cred-key').fill('sk-or-good'); await dlg.locator('#cred-test').click()
  await expect(dlg.locator('#cred-test-result')).toContainText('Đã kết nối · 2 model')

  // Ollama: default base URL placeholder, Docker hint, unreachable → PROVIDER_UNREACHABLE, then the fake server
  await chooseProvider(page, 'Ollama (cục bộ)')
  await expect(dlg.locator('#cred-base')).toHaveAttribute('placeholder', 'http://localhost:11434')
  await expect(dlg.locator('#cred-docker-hint')).toContainText('host.docker.internal')
  await dlg.locator('#cred-base').fill('http://127.0.0.1:9'); await dlg.locator('#cred-test').click()
  await expect(dlg.locator('#cred-test-result')).toContainText('Không kết nối được ollama')
  await dlg.locator('#cred-base').fill(`${CHAT}/ollama`); await dlg.locator('#cred-test').click()
  await expect(dlg.locator('#cred-test-result')).toContainText('Đã kết nối · 2 model')
  await dlg.locator('#cred-name').fill(name); await dlg.locator('#cred-add').click()
  const row = dlg.locator(`[data-cred="${name}"]`)
  await expect(row).toContainText('Ollama (cục bộ)'); await expect(row).not.toContainText('••••')  // key cleared on provider switch
  await row.getByRole('button', { name: `Kiểm tra kết nối ${name}` }).click()
  await expect(row).toContainText('Đã kết nối · 2 model')
  await page.keyboard.press('Escape')

  // LLM node: pick the credential, load models, choose one; manual entry stays possible
  await page.goto('/workflows/example')
  for (const id of ['classify', 'answer']) {
    await page.locator(`.react-flow__node[data-id="${id}"]`).click(); await page.locator('#config-tab-settings').click()
    await page.locator('#llm-credential').click(); await page.getByRole('option', { name: new RegExp(name) }).click()
    await page.locator('#llm-model-load').click()
    await page.locator('#llm-model-select').click(); await page.getByRole('option', { name: 'qwen2.5:7b' }).click()
    await expect(page.locator('#llm-model')).toHaveValue('qwen2.5:7b')
  }
  await page.locator('#llm-model').fill('not-pulled'); await expect(page.locator('#llm-model')).toHaveValue('not-pulled')
  await page.locator('#llm-model').fill('llama3.2:latest')
  await page.locator('#run-btn').click()
  // the fake Ollama answers "order_status" to the classify prompt and reports 5 + 3 tokens (real usage, not an estimate)
  await expect(page.getByRole('button', { name: /classify · 8 tok/ })).toBeVisible({ timeout: 20_000 })
  await expect(page.getByRole('button', { name: /Lookup order/ })).toBeVisible()

  await page.goto('/workflows'); await page.locator('#creds-btn').click()
  await page.getByRole('dialog').getByRole('button', { name: `Xoá ${name}` }).click(); await confirmDelete(page, name)
  await expect(page.getByRole('dialog')).not.toContainText(name)
})
