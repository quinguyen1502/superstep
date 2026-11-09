import { generateKeyPairSync } from 'crypto'
import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { confirmDelete } from './confirm'
import { vt } from './catalog'

const fixtureKey = generateKeyPairSync('rsa', { modulusLength: 2048 }).privateKey.export({ type: 'pkcs8', format: 'pem' }).toString()
const serviceAccount = JSON.stringify({ type: 'service_account', client_email: 'fixture@example-project.iam.gserviceaccount.com', private_key: fixtureKey })
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`managed connections configure, discover, run and delete (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 })
    const headers = await login(page), suffix = `${lang}-${theme}`
    const channel = (await (await page.request.post('/api/approvals/channels', { headers, data: {
      kind: 'telegram', name: `Bot ${suffix}`, bot_token: '123456:AAbbCCddEEffGGhhIIjjKKll', webhook_secret: 'fixture-only-webhook-secret',
    } })).json()).data
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    const start = async (name: string, adapter: string) => {
      await page.goto('/settings/mcp'); await page.locator('#mcp-add').click()
      await page.locator('#mcp-new-name').fill(name)
      await page.locator('#mcp-new-transport').click()
      await page.getByRole('option', { name: lang === 'en' ? 'Managed connection' : vt('managedTools.transport'), exact: true }).click()
      await page.locator('#mcp-new-adapter').click()
      await page.getByRole('option', { name: adapter, exact: true }).click()
    }
    const googleName = `Sheets ${suffix}`
    await start(googleName, lang === 'en' ? 'Google Sheets' : 'Thao tác Google Sheets')
    await page.locator('#mcp-new-spreadsheet_id').fill('fixture-spreadsheet-123')
    await expect(page.locator('#mcp-new-sheet_name')).toHaveValue('')
    await expect(page.locator('#mcp-new-data_columns')).toHaveValue('')
    await page.locator('#mcp-new-sheet_name').fill('Requests')
    await page.locator('#mcp-new-data_columns').fill('6')
    if (process.env.REVIEW_SHOTS) await page.locator('#mcp-new').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-sheets-${suffix}.png` })
    await page.locator('#mcp-new-service_account').fill(serviceAccount)
    await page.locator('#mcp-create').click()
    const googleCard = page.locator('[data-testid^="mcp-card-"]', { hasText: googleName })
    await expect(googleCard).toBeVisible()
    await expect(googleCard).not.toContainText('PRIVATE KEY')
    await googleCard.locator('[id$="-discover"]').click()
    await expect(googleCard.getByTestId('mcp-tools')).toContainText('append_row')

    const telegramName = `Telegram ${suffix}`
    await start(telegramName, lang === 'en' ? 'Telegram actions' : 'Thao tác Telegram')
    await page.locator('#mcp-new-channel_id').click()
    await page.getByRole('option', { name: new RegExp(`Bot ${suffix}`) }).click()
    await page.locator('#mcp-new-chat_id').fill('-100123')
    if (process.env.REVIEW_SHOTS) await page.locator('#mcp-new').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-telegram-${suffix}.png` })
    await page.locator('#mcp-create').click()
    const telegramCard = page.locator('[data-testid^="mcp-card-"]', { hasText: telegramName })
    await expect(telegramCard).toBeVisible()
    await telegramCard.locator('[id$="-discover"]').click()
    await expect(telegramCard.getByTestId('mcp-tools')).toContainText('send_message')
    const servers = (await (await page.request.get('/api/mcp/servers', { headers })).json()).data.servers
    const server = servers.find((item: any) => item.name === telegramName)
    const graph: any = SIMPLE(`Managed ${suffix}`)
    graph.state.push({ name: 'result', type: 'object' })
    graph.nodes[1].type = 'mcp'
    graph.nodes[1].data = { label: 'Send', server_id: '', tool: '', output_field: 'result', arguments: {} }
    const wid = await newWorkflow(page, headers, graph)
    await page.goto(`/workflows/${wid}`)
    await page.locator('.react-flow__node[data-id="reply"]').click()
    await page.locator('#config-tab-settings').click()
    await page.locator('#mcp-server').click()
    await page.getByRole('option', { name: `${telegramName} · managed`, exact: true }).click()
    await page.locator('#mcp-tool').click()
    await page.getByRole('option', { name: 'send_message', exact: true }).click()
    await page.locator('#mcp-arg-text').fill('Hello from managed tool')
    await page.locator('#save-btn').click()
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await page.goto('/settings/mcp')
    const operations = page.locator(`[data-testid="mcp-card-${server.id}"]`).getByTestId('managed-operations')
    await expect(operations.locator('[data-outcome="confirmed"]')).toHaveCount(1)
    const unknown = { operation_id: 'fixture-unknown', key: 'fixture', tool: 'send_message', outcome: 'unknown', created: Date.now() / 1000 }
    await page.route(`**/api/mcp/servers/${server.id}/operations`, route => route.fulfill({ json: { success: true, data: [unknown], error: null } }))
    await page.route(`**/api/mcp/servers/${server.id}/operations/fixture-unknown/reconcile`, route => route.fulfill({ status: 409,
      json: { success: false, data: null, error: { code: 'MANAGED_OUTCOME_UNKNOWN', details: { operation: 'fixture-unknown' } } } }))
    await operations.getByRole('button', { name: lang === 'en' ? 'Refresh' : vt('managedTools.refresh'), exact: true }).click()
    await expect(operations.locator('[data-outcome="unknown"]')).toBeVisible()
    await operations.getByRole('button', { name: lang === 'en' ? 'Check external result' : vt('managedTools.reconcile'), exact: true }).click()
    await expect(operations.getByRole('alert')).toContainText('fixture-unknown')
    if (process.env.REVIEW_SHOTS) await operations.screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-unknown-${suffix}.png` })
    const card = page.locator(`[data-testid="mcp-card-${server.id}"]`)
    await card.locator('[id$="-edit"]').click()
    await card.locator('[id$="-delete"]').click(); await confirmDelete(page, telegramName)
    await expect(card).toHaveCount(0)
  })
}
