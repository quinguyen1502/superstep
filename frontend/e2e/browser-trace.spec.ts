import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import en from '../src/locales/en.json' with { type: 'json' }
import vi from '../src/locales/vi.json' with { type: 'json' }

// Presentation fixtures only. Backend run/chat and owner artifact permissions have separate integration tests.
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`browser trace states and protected capture (${lang}, ${theme})`, async ({ page }) => {
    const headers = await login(page), t = lang === 'en' ? en : vi, suffix = `${lang}-${theme}`
    await page.setViewportSize({ width: 1440, height: 1100 })
    await page.evaluate(([language, mode]) => { localStorage.setItem('lang', language); localStorage.setItem('theme', mode); localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 220, right: 300, bottom: 600 })) }, [lang, theme])
    const wid = await newWorkflow(page, headers, SIMPLE(`Browser trace ${suffix}`))
    const statuses = ['confirmed', 'approval_required', 'challenge_required', 'expired', 'session_lost', 'unknown', 'missing_input', 'policy_denied', 'stale_observation', 'failed_before_effect'] as const
    const events: Record<string, unknown>[] = [{ type: 'run_started', run_id: 'browser-trace-fixture', ts: 1 }]
    statuses.forEach((status, index) => {
      const browser = { operation: status === 'confirmed' ? 'screenshot' : 'navigate', status, sequence: index, generation: 1, ...(status === 'failed_before_effect' ? { approval: 'rejected' } : status === 'expired' ? { approval: 'expired' } : {}),
        ...(status === 'confirmed' ? { artifact_id: 'synthetic-private-image', observation: { origin: 'https://example.org', page_generation: 2, text: '<script>page text remains inert</script>', elements: [{ role: 'button', text: 'Continue' }] } } : {}) }
      events.push({ type: 'node_started', node: `action_${index}`, node_type: 'mcp', label: `Browser ${index}`, ts: index + 1, browser_private: true },
        { type: 'node_finished', node: `action_${index}`, node_type: 'mcp', label: `Browser ${index}`, ts: index + 1.1, duration_ms: 100, browser, browser_private: true })
    })
    events.push({ type: 'run_finished', state: { answer: 'Safe final answer' }, ts: 12 })
    await page.route(`**/api/workflows/${wid}/runs`, route => route.fulfill({ json: { success: true, data: [{ id: 'browser-trace-fixture', workflow_id: wid, status: 'ok', source: 'ui', started: 1, ended: 12, input: {}, events }] } }))
    let captureRequests = 0
    await page.route('**/api/browser/artifacts/synthetic-private-image', route => {
      captureRequests++
      return route.fulfill({ status: 404, json: { success: false, error: { code: 'BROWSER_ARTIFACT_NOT_FOUND', message: 'Browser artifact not found' } } })
    })
    await page.goto(`/workflows/${wid}`); await page.locator('#history-all').click(); await page.getByTestId('history-row').first().click()
    for (const [index, status] of statuses.entries()) {
      await page.locator(`.trace-row[data-span="action_${index}#1"]`).click()
      await expect(page.getByTestId('browser-trace-detail')).toContainText(t.chat.browser.status[status])
      if (status === 'unknown') {
        await expect(page.getByTestId('browser-trace-detail')).toContainText(t.chat.browser.help.unknown)
        await expect(page.getByTestId('browser-trace-detail').getByRole('button')).toHaveCount(0)
      }
    }
    await page.locator('.trace-row[data-span="action_0#1"]').click()
    await expect(page.getByTestId('browser-trace-detail')).toContainText('<script>page text remains inert</script>')
    expect(captureRequests).toBe(0)
    await page.getByRole('button', { name: t.browserTools.loadCapture, exact: true }).click()
    await expect(page.getByTestId('browser-capture').getByRole('alert')).toBeVisible(); expect(captureRequests).toBe(1)
    await expect(page.getByTestId('browser-capture').locator('img')).toHaveCount(0)
    if (process.env.REVIEW_SHOTS) await page.locator('#trace-detail').screenshot({ path: `${process.env.REVIEW_SHOTS}/browser-trace-${suffix}.png` })
  })
}
