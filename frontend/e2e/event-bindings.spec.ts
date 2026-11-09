import { createHmac } from 'crypto'
import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { confirmDelete } from './confirm'
import { vt } from './catalog'

const SECRET = 'fixture-only-event-signing-secret-0123456789'
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`event binding config, signed input and typed deletion (${lang}, ${theme})`, async ({ page }) => {
    const headers = await login(page), suffix = `${lang}-${theme}`
    const channel = (await (await page.request.post('/api/approvals/channels', { headers,
      data: { kind: 'webhook', name: `Events ${suffix}`, signing_secret: SECRET } })).json()).data
    const graph = SIMPLE(`Events ${suffix}`)
    graph.state.push({ name: 'context', type: 'object', reducer: 'replace' } as any)
    const wid = await newWorkflow(page, headers, graph)
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    await page.goto(`/workflows/${wid}`)
    await page.locator('#more-btn').click(); await page.locator('#chat-triggers-btn').click()
    await page.locator('#chat-trigger-channel').click()
    await page.getByRole('option', { name: new RegExp(`Events ${suffix}`) }).click()
    await expect(page.locator('#event-binding-settings')).toBeVisible()
    await page.locator('#chat-trigger-name').fill(`Expenses ${suffix}`)
    await page.locator('#chat-trigger-place').fill('expenses')
    await expect(page.locator('#chat-trigger-save')).toBeDisabled()
    await page.locator('#event-senders').fill('employee-42')
    await page.locator('#event-map-message').fill('data.text')
    await page.locator('#event-map-context').fill('$')
    if (process.env.REVIEW_SHOTS) await page.locator('#chat-triggers-dialog').screenshot({ path: `${process.env.REVIEW_SHOTS}/event-binding-${suffix}.png` })
    await page.locator('#chat-trigger-save').click()
    const row = page.locator(`[data-testid="chat-trigger-row"][data-name="Expenses ${suffix}"]`)
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: lang === 'en' ? `Edit chat trigger Expenses ${suffix}` : vt('chatTriggers.editFor', { name: `Expenses ${suffix}` }) }).click()
    await expect(page.locator('#event-senders')).toHaveValue('employee-42')
    await expect(page.locator('#event-map-context')).toHaveValue('$')
    const body = JSON.stringify({ id: `expense-${suffix}`, type: 'message.text', time: '2026-11-01T10:00:00+07:00', place: 'expenses', sender: 'employee-42', data: { text: 'Lunch 50000' } })
    const timestamp = Math.floor(Date.now() / 1000)
    const signature = `t=${timestamp},v1=${createHmac('sha256', SECRET).update(`${timestamp}.${body}`).digest('hex')}`
    const response = await page.request.post(channel.callback_path, { data: body, headers: { 'Content-Type': 'application/json', 'X-Studio-Signature': signature } })
    expect(response.ok()).toBeTruthy()
    expect((await response.json()).data.outcome).toBe('queued')
    await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers })).json()).data.length).toBe(1)
    await row.getByRole('switch').click(); await expect(row.getByRole('switch')).not.toBeChecked()
    await row.getByRole('button', { name: lang === 'en' ? `Delete chat trigger Expenses ${suffix}` : vt('chatTriggers.deleteFor', { name: `Expenses ${suffix}` }) }).click()
    await confirmDelete(page, `Expenses ${suffix}`)
    await expect(row).toHaveCount(0)
  })
}
