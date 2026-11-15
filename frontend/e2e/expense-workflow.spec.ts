import { generateKeyPairSync } from 'crypto'
import { readFileSync } from 'fs'
import path from 'path'
import { test, expect } from '@playwright/test'
import { login } from './helpers'

test.skip(process.env.E2E_EXPENSE_FIXTURE !== '1', 'Requires the isolated Google/model fixture; use E2E_EXPENSE_FIXTURE=1 E2E_CODE_RUNTIME=subprocess')
const TEMPLATE = path.resolve('../examples/telegram-expenses.template.json')
const privateKey = generateKeyPairSync('rsa', { modulusLength: 2048 }).privateKey.export({ type: 'pkcs8', format: 'pem' }).toString()
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`expense template: import, bind, event, failover and confirmed write (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1800, height: 1300 })
    const headers = await login(page), suffix = `${lang}-${theme}`
    const chatId = `-100123${lang === 'en' ? '1' : '2'}${theme === 'light' ? '1' : '2'}`
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    await page.goto('/workflows'); await page.locator('#new-wf').click()
    const payload = JSON.parse(readFileSync(TEMPLATE, 'utf8'))
    payload.name = `Expense review ${suffix}`
    await page.locator('#tpl-import-file').setInputFiles({ name: 'telegram-expenses.template.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(payload)) })
    const card = page.locator('[data-testid="tpl-card"]', { hasText: payload.name })
    await expect(card).toBeVisible(); await card.getByRole('button').first().click()
    await expect(page).toHaveURL(/\/workflows\/[^/]+$/)
    const wid = page.url().split('/').pop()!
    await expect(page.locator('.react-flow__node')).toHaveCount(12)
    await expect(page.locator('#validation-errors')).toBeVisible()
    const channel = (await (await page.request.post('/api/approvals/channels', { headers, data: {
      kind: 'telegram', name: `Expense bot ${suffix}`, bot_token: '123456:AAbbCCddEEffGGhhIIjjKKll', webhook_secret: 'fixture-expense-webhook-secret',
    } })).json()).data
    const create = async (data: any) => {
      const response = await page.request.post('/api/mcp/servers', { headers, data })
      expect(response.ok()).toBeTruthy(); return (await response.json()).data
    }
    const telegram = await create({ name: `Expense replies ${suffix}`, transport: 'managed', adapter: 'telegram', settings: { channel_id: channel.id, chat_id: chatId } })
    const spreadsheet = `fixture-expenses-${suffix}`
    const google = await create({ name: `Expense rows ${suffix}`, transport: 'managed', adapter: 'google_sheets',
      settings: { spreadsheet_id: spreadsheet, sheet_name: 'Expenses', data_columns: 7 },
      secrets: { service_account: JSON.stringify({ type: 'service_account', client_email: 'fixture@example-project.iam.gserviceaccount.com', private_key: privateKey }) } })
    const credential = async (provider: string) => {
      const response = await page.request.post('/api/credentials', { headers, data: { name: `Expense ${provider} ${suffix}`, provider, api_key: provider === 'openrouter' ? 'fixture-model-key' : '' } })
      expect(response.ok()).toBeTruthy(); return (await response.json()).data.id
    }
    const primary = await credential('openrouter'), backup = await credential('ollama')
    const graph = (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data
    for (const node of graph.nodes) {
      if (node.type === 'mcp') node.data.server_id = node.data.tool === 'append_row' ? google.id : telegram.id
      if (node.type === 'llm') { node.data.credential_id = primary; node.data.fallback.credential_id = backup }
    }
    const saved = await page.request.post('/api/workflows', { headers, data: graph })
    expect((await saved.json()).data.errors).toEqual([])
    const binding = await page.request.post(`/api/workflows/${wid}/chat-triggers`, { headers, data: {
      name: 'Expense intake', channel_id: channel.id, place: chatId, event: { senders: ['42'], type: 'message.text', mapping: { message: 'data.text', context: '$' } },
    } })
    expect(binding.ok()).toBeTruthy()
    const event = { update_id: Date.now(), message: { message_id: 101, date: 1793557800, from: { id: 42, first_name: 'Sample employee' },
      chat: { id: Number(chatId), type: 'supergroup' }, text: 'Lunch 50000 on 2026-10-31' } }
    const send = () => page.request.post(channel.callback_path, { data: event, headers: { 'X-Telegram-Bot-Api-Secret-Token': 'fixture-expense-webhook-secret' } })
    expect((await (await send()).json()).data.outcome).toBe('queued')
    let run: any
    await expect.poll(async () => {
      run = (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers })).json()).data[0]
      return run?.status
    }, { timeout: 25_000 }).toBe('ok')
    expect((await (await send()).json()).data.outcome).toBe('duplicate')
    const rows = (await (await page.request.get('/api/_expense-fixture')).json()).data.rows[spreadsheet]
    expect(rows).toHaveLength(1)
    expect(rows[0].values.slice(0, 6)).toEqual(['2026-10-31', 'Sample employee', 'Lunch', 'Food', 50000, 'Pending approval'])
    expect(rows[0].values).toHaveLength(8)
    await page.goto(`/workflows/${wid}?run=${run.id}`)
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 15_000 })
    await page.locator('#run-input').fill(JSON.stringify(run.input, null, 2))
    if (process.env.REVIEW_SHOTS) await page.screenshot({ path: `${process.env.REVIEW_SHOTS}/expense-workflow-${suffix}.png` })
    await page.locator('.trace-row[data-span="append#1"]').click()
    await page.locator('#trace-detail').getByRole('tab', { name: 'Output', exact: true }).click()
    await expect(page.locator('#trace-detail')).toContainText('confirmed')
    if (process.env.REVIEW_SHOTS) await page.locator('#trace-detail').screenshot({ path: `${process.env.REVIEW_SHOTS}/expense-confirmed-${suffix}.png` })
  })
}
