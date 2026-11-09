import { createHmac } from 'crypto'
import { test, expect, type Page } from '@playwright/test'
import { confirmDelete } from './confirm'
import { login, newWorkflow, SIMPLE } from './helpers'
// the editor's Chat triggers dialog (add, duplicate command refused, on/off, edit, delete by name), a signed
// Slack mention that starts a run (Chat badge in History), and the Channels page's events URL and scope warning.
// Slack is the fake API of backend/tests/fixtures/mock_chat_api.py; checks and replies are covered by test_chat_trigger_runs.py.
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
const SIGNING = '0123456789abcdef0123456789abcdef'
async function sent(page: Page, method: string, match: (b: any) => boolean) {
  let found: any = null
  await expect.poll(async () => { const calls = await (await page.request.get(`${CHAT}/_messages`)).json(); found = calls.filter((c: any) => c.method === method && match(c.body)).pop(); return !!found }).toBe(true)
  return found.body
}

test('chat triggers: add, refuse a duplicate command, switch, edit, delete; a mention starts a run', async ({ page }) => {
  const H = await login(page); const team = `TCT${Date.now().toString(36).toUpperCase()}`
  const wid = await newWorkflow(page, H, SIMPLE(`Chat ${Date.now()}`))
  const ch = (await (await page.request.post('/api/approvals/channels', { headers: H, data: { kind: 'slack', name: `Acme ${team}`, bot_token: `xoxb-1-${team}-abcdefgh`, signing_secret: SIGNING } })).json()).data
  // the admin's Slack account in that workspace, verified with the code the bot sent
  await page.request.put('/api/approvals/identities', { headers: H, data: { kind: 'slack', team_id: team, external_id: 'U0CHAT' } })
  await page.request.post('/api/approvals/identities/slack/send-code', { headers: H, data: { team_id: team } })
  const code = (await sent(page, 'chat.postMessage', b => b.channel === 'U0CHAT')).text.match(/\d{6}/)[0]
  expect((await page.request.post('/api/approvals/identities/slack/verify', { headers: H, data: { team_id: team, code } })).ok()).toBe(true)

  await page.goto(`/workflows/${wid}`)
  await page.locator('#more-btn').click(); await page.locator('#chat-triggers-btn').click()
  const dlg = page.locator('#chat-triggers-dialog'); await expect(dlg).toBeVisible()
  await expect(dlg.getByText('Chưa có chat trigger nào.')).toBeVisible()
  await page.locator('#chat-trigger-channel').click(); await page.getByRole('option', { name: new RegExp(`Acme ${team}`) }).click()
  await page.locator('#chat-trigger-where').click(); await page.getByRole('option', { name: 'Một kênh Slack' }).click()
  await page.locator('#chat-trigger-place').fill('C0E2EHR')
  await page.locator('#chat-trigger-command').fill('two words'); await expect(page.locator('#chat-trigger-command-hint')).toBeVisible()
  await expect(page.locator('#chat-trigger-save')).toBeDisabled()
  await page.locator('#chat-trigger-command').fill('Ask'); await expect(page.locator('#chat-trigger-sample')).toContainText('@bot ask <nội dung>')
  await expect(page.locator('#chat-trigger-input')).toContainText('message'); await expect(page.locator('#chat-trigger-reply')).toContainText('answer')
  await page.locator('#chat-trigger-name').fill('Support'); await page.locator('#chat-trigger-save').click()
  const row = dlg.locator('[data-testid=chat-trigger-row][data-name="Support"]')
  await expect(row).toContainText('ask'); await expect(row.getByTestId('chat-trigger-where')).toContainText('kênh C0E2EHR')
  const saved = (await (await page.request.get(`/api/workflows/${wid}/chat-triggers`, { headers: H })).json()).data
  expect(saved).toHaveLength(1); expect(saved[0]).toMatchObject({ name: 'Support', place: 'C0E2EHR', command: 'ask', input_field: 'message', reply_field: 'answer', enabled: true })

  // the same command in the same place is refused, with the translated error
  await page.locator('#chat-trigger-where').click(); await page.getByRole('option', { name: 'Một kênh Slack' }).click()
  await page.locator('#chat-trigger-place').fill('C0E2EHR'); await page.locator('#chat-trigger-command').fill('ask'); await page.locator('#chat-trigger-save').click()
  await expect(dlg.getByRole('alert')).toContainText("Một chat trigger khác đã dùng lệnh 'ask' ở đó")

  // a mention in that channel starts a run as the linked user; the bot answers in the thread
  const body = JSON.stringify({ type: 'event_callback', team_id: team, event_id: `Ev${Date.now()}`, authorizations: [{ user_id: 'UBOT' }],
    event: { type: 'app_mention', user: 'U0CHAT', text: '<@UBOT> ask where is my order', channel: 'C0E2EHR', ts: '1700.5' } })
  const ts = String(Math.floor(Date.now() / 1000)), sig = 'v0=' + createHmac('sha256', SIGNING).update(`v0:${ts}:${body}`).digest('hex')
  const res = await page.request.post('/api/channels/events/slack', { data: body, headers: { 'Content-Type': 'application/json', 'X-Slack-Request-Timestamp': ts, 'X-Slack-Signature': sig } })
  expect((await res.json()).data).toEqual({ outcome: 'queued' })
  expect((await sent(page, 'chat.postMessage', b => b.thread_ts === '1700.5' && /đã xong|finished/.test(b.text))).text).toContain('Chat ')

  // switch off and on, edit the command, delete by typed name
  await row.getByRole('switch').click(); await expect(row.getByRole('switch')).not.toBeChecked()
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/chat-triggers`, { headers: H })).json()).data[0].enabled).toBe(false)
  await row.getByRole('switch').click(); await expect(row.getByRole('switch')).toBeChecked()
  await row.getByRole('button', { name: 'Sửa chat trigger Support' }).click()
  await expect(page.locator('#chat-trigger-command')).toHaveValue('ask'); await page.locator('#chat-trigger-command').fill('hoi'); await page.locator('#chat-trigger-save').click()
  await expect(row).toContainText('hoi'); await expect(row).toContainText('tin nhắn gần nhất')
  await row.getByRole('button', { name: 'Xoá chat trigger Support' }).click(); await confirmDelete(page, 'Support')
  await expect(dlg.getByText('Chưa có chat trigger nào.')).toBeVisible()
  await page.keyboard.press('Escape')

  // History (loaded when the editor opens, so reload): the run from the chat carries the Chat badge
  await page.reload(); await page.locator('#history-all').click()
  await expect(page.locator('[data-testid=history-row]').first().locator('[data-testid=history-source]')).toHaveText('Chat')
  await expect(page.locator('[data-testid=history-row]').first().locator('[data-channel-logo=slack]')).toBeVisible()

  // Channels: the Slack connection shows its events URL; missing scopes are flagged (response stubbed: the fake API sends none)
  await page.route('**/api/approvals/channels', async r => {
    const resp = await r.fetch(); const json = await resp.json()
    for (const c of json.data.channels) if (c.id === ch.id) c.chat.missing_scopes = ['app_mentions:read', 'im:history']
    await r.fulfill({ response: resp, json })
  })
  await page.goto('/settings/channels')
  const conn = page.locator(`[data-channel-id="${ch.id}"]`)
  await expect(conn.locator(`#ch-${ch.id}-events`)).toHaveValue(/\/api\/channels\/events\/slack$/)
  await expect(conn.locator(`#ch-${ch.id}-scopes`)).toContainText('app_mentions:read, im:history')
})
