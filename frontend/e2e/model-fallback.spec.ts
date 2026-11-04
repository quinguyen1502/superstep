import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { expectRowAligned, settled } from './helpers/alignment'

const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`model fallback persists, runs and disables (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    const headers = await login(page)
    const credential = async (name: string, base_url: string) => {
      const response = await page.request.post('/api/credentials', { headers, data: { name, provider: 'ollama', base_url } })
      expect(response.ok()).toBeTruthy()
      return (await response.json()).data.id as string
    }
    const suffix = `${lang}-${theme}`
    const primary = await credential(`Primary unreachable ${suffix}`, 'http://127.0.0.1:9')
    const backup = await credential(`Local backup ${suffix}`, `${CHAT}/ollama`)
    const graph = SIMPLE('Model policy review')
    Object.assign(graph.nodes[1].data, { credential_id: primary, model: 'first' })
    const wid = await newWorkflow(page, headers, graph)
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    await page.goto(`/workflows/${wid}`)
    await page.locator('.react-flow__node[data-id="reply"]').click()
    await page.locator('#config-tab-settings').click()
    await page.locator('#model-fallback-enabled').click()
    await page.locator('#model-fallback-credential').click()
    await page.getByRole('option', { name: `Local backup ${suffix} · ollama`, exact: true }).click()
    await page.locator('#model-fallback-model').fill('llama3.2:latest')
    await settled(page.locator('#model-fallback-settings'))
    await expectRowAligned(await page.locator('#model-fallback-model').locator('..').locator('> *').all(), { label: 'fallback model controls' })
    if (process.env.REVIEW_SHOTS) await page.locator('#model-fallback-settings').screenshot({ path: `${process.env.REVIEW_SHOTS}/model-fallback-${lang}-${theme}.png` })
    await page.locator('#save-btn').click()
    await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data.nodes[1].data.fallback)
      .toEqual({ credential_id: backup, model: 'llama3.2:latest' })
    await page.reload()
    await page.locator('.react-flow__node[data-id="reply"]').click()
    await page.locator('#config-tab-settings').click()
    await expect(page.locator('#model-fallback-enabled')).toBeChecked()
    await expect(page.locator('#model-fallback-model')).toHaveValue('llama3.2:latest')
    await page.locator('#run-btn').click()
    await page.locator('.trace-row[data-span="reply#1"]').click()
    await page.locator('#trace-detail').getByRole('tab', { name: lang === 'en' ? 'Raw' : 'Thô', exact: true }).click()
    await expect(page.locator('#trace-detail')).toContainText('model_attempts', { timeout: 20_000 })
    const attempts = page.locator('#trace-detail').getByText('model_attempts:', { exact: true }).locator('..')
    const expand = lang === 'en' ? 'Expand' : 'Mở rộng'
    await attempts.getByRole('button', { name: expand, exact: true }).click()
    while (await attempts.getByRole('button', { name: expand, exact: true }).count())
      await attempts.getByRole('button', { name: expand, exact: true }).first().click()
    await expect(page.locator('#trace-detail')).toContainText('PROVIDER_UNREACHABLE')
    await expect(page.locator('#trace-detail')).toContainText('llama3.2:latest')
    await page.locator('#model-fallback-enabled').click()
    await page.locator('#save-btn').click()
    await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data.nodes[1].data.fallback)
      .toBeUndefined()
  })
}
