import { createHmac } from 'crypto'
import { test, expect, type Page } from '@playwright/test'
import { apiToken } from './helpers'
// connect Slack, link my Slack account, pick the channel on a Human node, see the request in the audit log.
// Slack/Telegram are the fake APIs of backend/tests/fixtures/mock_chat_api.py (CHAT port), which record every message,
// so the test reads the verification code the "bot" sent and the approval request it posted.
const WF = {
  name: `Channel approval e2e ${Date.now()}`, state: [{ name: 'message', type: 'string' }, { name: 'decision', type: 'string' }],
  nodes: [{ id: 's', type: 'start', position: { x: 40, y: 150 }, data: { label: 'Start' } },
    { id: 'ask', type: 'human', position: { x: 300, y: 150 }, data: { label: 'Manager approval', prompt: 'Approve refund?', output_field: 'decision' } },
    { id: 'e', type: 'end', position: { x: 560, y: 150 }, data: { label: 'End' } }],
  edges: [{ id: '1', source: 's', target: 'ask' }, { id: '2', source: 'ask', target: 'e' }],
}
const CHAT = `http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}`
async function sent(page: Page, method: string, match: (b: any) => boolean) {
  let found: any = null
  await expect.poll(async () => { const calls = await (await page.request.get(`${CHAT}/_messages`)).json(); found = calls.filter((c: any) => c.method === method && match(c.body)).pop(); return !!found }).toBe(true)
  return found.body
}
async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
  return apiToken(page)
}

test('approval channels: org connection, verified account, Human node, request, audit', async ({ page }) => {
  const token = await login(page); const auth = { Authorization: `Bearer ${token}` }
  const wid = (await (await page.request.post('/api/workflows', { headers: auth, data: WF })).json()).data.id
  await page.goto(`/workflows/${wid}`)
  // node settings: Studio only by default; nothing connected yet
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#approval-channel')).toContainText('Chỉ trong Studio')
  await expect(page.locator('#approval-no-channels')).toBeVisible()
  // Settings → Channels (own URL): one card per platform, Not set up yet
  await page.locator('#user-menu').click(); await page.locator('#settings-item').click()
  await expect(page).toHaveURL(/\/settings\/channels$/)
  const slack = page.locator('[data-testid=channel-card-slack]'), tg = page.locator('[data-testid=channel-card-telegram]')
  await expect(slack.getByTestId('status')).toHaveText('Chưa thiết lập'); await expect(tg.getByTestId('status')).toHaveText('Chưa thiết lập')
  // each platform card title carries its logo
  for (const k of ['slack', 'telegram', 'whatsapp', 'email', 'teams'])
    await expect(page.locator(`[data-testid=channel-card-${k}] [data-channel-logo=${k}]`).first()).toBeVisible()
  // connect Slack for the whole organization (the demo user is an admin): Org tab inside the Slack card
  await expect(slack.locator('#channel-card-slack-toggle')).toHaveAttribute('aria-expanded', 'false')
  await slack.locator('#channel-card-slack-toggle').click()
  await slack.locator('#channel-card-slack-tab-org').click()
  const add = slack.locator('[data-testid=add-slack-org]'), save = add.locator('#add-slack-org-save'); await expect(save).toBeDisabled()
  await add.locator('#add-slack-org-name').fill('Acme')
  await add.locator('#add-slack-org-bot_token').fill('nope'); await add.locator('#add-slack-org-signing_secret').fill('0123456789abcdef0123456789abcdef'); await save.click()
  await expect(add.getByRole('alert')).toContainText('bot_token')  // CHANNEL_CONFIG_INVALID, translated
  await add.locator('#add-slack-org-bot_token').fill('xoxb-1111-2222-e2etoken'); await save.click()
  const card = slack.locator('[data-testid=channel-slack-org]')
  await expect(card).toContainText('••••oken'); await expect(card).toContainText('Acme')
  await expect(slack.getByTestId('status')).toHaveText('Đã kết nối'); await expect(slack).toContainText('Toàn tổ chức')
  await expect(card.locator('input[readonly][id$="-shared"]')).toHaveValue(/\/api\/approvals\/callback\/slack$/)  // shared URL, routed by team_id
  await expect(card).toContainText('(2222)')  // workspace id read with auth.test
  const cid = await card.getAttribute('data-channel-id')
  await card.locator(`#ch-${cid}-test`).click(); await expect(card.getByRole('alert')).toContainText('Kết nối hoạt động (Workspace 2222)')
  // search + filters
  await page.locator('#channel-filters-search').fill('acme'); await expect(slack).toBeVisible(); await expect(tg).toHaveCount(0)
  await page.locator('#channel-filters-search').fill('zzz'); await expect(page.locator('#channels-none')).toBeVisible()
  await page.locator('#channel-filters-search').fill('')
  await page.locator('#channel-filters-status').click(); await page.getByRole('option', { name: 'Chưa thiết lập' }).click()
  await expect(tg).toBeVisible(); await expect(slack).toHaveCount(0)
  await page.locator('#channel-filters-status').click(); await page.getByRole('option', { name: 'Mọi trạng thái' }).click()
  await page.locator('#channel-filters-scope').click(); await page.getByRole('option', { name: 'Cá nhân' }).click()
  await expect(page.locator('#channels-none')).toBeVisible()
  await page.locator('#channel-filters-scope').click(); await page.getByRole('option', { name: 'Mọi phạm vi' }).click()
  // my Slack account, inline in the card: link -> the bot DMs a code -> wrong code refused -> right code verifies
  const acct = slack.locator('[data-testid=id-slack-2222]')
  await expect(acct.locator('[data-channel-logo=slack]')).toBeVisible()  // my account row and the connection carry the logo
  await expect(slack.locator('[data-testid=channel-slack-org] [data-channel-logo=slack]')).toBeVisible()
  await acct.locator('#id-slack-2222').fill('lower-case'); await acct.locator('#id-slack-2222-link').click()
  await expect(acct.getByRole('alert')).toContainText('Slack')  // IDENTITY_INVALID
  await acct.locator('#id-slack-2222').fill('U0E2EADMIN'); await acct.locator('#id-slack-2222-link').click()
  await expect(acct).toContainText('Nhập mã 6 số')
  const code = (await sent(page, 'chat.postMessage', b => b.channel === 'U0E2EADMIN')).text.match(/\d{6}/)[0]
  await acct.locator('#id-slack-2222-code').fill(code === '000000' ? '111111' : '000000'); await acct.locator('#id-slack-2222-verify').click()
  await expect(acct.getByRole('alert')).toContainText('còn 4 lần')  // IDENTITY_CODE_INVALID {left}
  await acct.locator('#id-slack-2222-code').fill(code); await acct.locator('#id-slack-2222-verify').click()
  await expect(acct.locator('#id-slack-2222-verified')).toBeVisible()
  // the same account under My accounts (own URL)
  await page.locator('#settings-nav-accounts').click(); await expect(page).toHaveURL(/\/settings\/accounts$/)
  await expect(page.locator('#id-slack-2222-verified')).toBeVisible()
  await page.goto(`/workflows/${wid}`)
  // reopen the editor (channels reload) and configure the node
  await page.locator('.react-flow__node[data-id="ask"]').click(); await page.locator('#config-tab-settings').click()
  await page.locator('#approval-channel').click()
  await expect(page.getByRole('option', { name: 'Slack · Acme · Toàn tổ chức' }).locator('[data-channel-logo=slack]')).toBeVisible()
  await page.getByRole('option', { name: 'Slack · Acme · Toàn tổ chức' }).click()
  await expect(page.locator('#approval-channel [data-channel-logo=slack]')).toBeVisible()
  await expect(page.locator('#approval-not-connected')).toHaveCount(0)
  await page.locator('#approval-target').fill('C0E2E'); await page.locator('#approval-approvers').fill('lead@example.com, ops@example.com')
  await expect(page.locator('#approval-approvers')).toHaveValue('lead@example.com, ops@example.com')
  await page.getByRole('button', { name: 'Lưu', exact: true }).click()
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}`, { headers: auth })).json()).data.nodes.find((n: any) => n.id === 'ask').data.approval)
    .toEqual({ channel_id: cid, channel: 'slack', target: 'C0E2E', approvers: ['lead@example.com', 'ops@example.com'] })
  // a run that pauses there posts the request (to the fake Slack API) and audits it
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'waiting', { timeout: 30_000 })
  const ed = page.url()
  await page.goto('/settings/audit'); await expect(page.locator('#settings-nav-audit')).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('[data-testid=audit-row]', { hasText: WF.name }).first()).toContainText('Đã gửi')
  await expect(page.locator('[data-testid=audit-row]', { hasText: WF.name }).first().locator('[data-channel-logo=slack]')).toBeVisible()
  const post = await sent(page, 'chat.postMessage', b => b.channel === 'C0E2E')
  expect(post.blocks[1].elements.map((e: any) => e.action_id)).toEqual(['approve', 'reject'])
  // in the language this user works in (vi UI -> preferences.lang = vi)
  expect(post.blocks[0].text.text).toContain('*Cần phê duyệt*'); expect(post.blocks[1].elements.map((e: any) => e.text.text)).toEqual(['Duyệt', 'Từ chối'])
  // Slack calls the shared URL when U0E2EADMIN (verified above, the run owner) presses Approve
  const body = new URLSearchParams({ payload: JSON.stringify({ type: 'block_actions', team: { id: '2222' }, user: { id: 'U0E2EADMIN' }, actions: [{ action_id: 'approve', value: post.blocks[1].elements[0].value }] }) }).toString()
  const ts = String(Math.floor(Date.now() / 1000)), sig = 'v0=' + createHmac('sha256', '0123456789abcdef0123456789abcdef').update(`v0:${ts}:${body}`).digest('hex')
  const res = await page.request.post('/api/approvals/callback/slack', { data: body, headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Slack-Request-Timestamp': ts, 'X-Slack-Signature': sig } })
  expect((await res.json()).data).toEqual({ outcome: 'approved' })
  await expect.poll(async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: auth })).json()).data[0].status, { timeout: 30_000 }).toBe('ok')
  expect((await sent(page, 'chat.update', b => b.channel === 'C0E2E')).text).toContain('admin@example.com đã duyệt')
  await page.reload()
  await expect(page.locator('[data-testid=audit-row]', { hasText: WF.name }).first()).toContainText('Đã duyệt')
  // audit filters: platform (with its logo), decision, text
  await page.locator('#audit-filters-kind').click()
  await expect(page.getByRole('option', { name: 'Slack' }).locator('[data-channel-logo=slack]')).toBeVisible(); await page.keyboard.press('Escape')
  await page.locator('#audit-filters-action').click(); await page.getByRole('option', { name: 'Đã duyệt' }).click()
  await expect(page.locator('[data-testid=audit-row]', { hasText: WF.name })).toHaveCount(1)
  await page.locator('#audit-filters-search').fill('no-such-workflow'); await expect(page.locator('[data-testid=audit-row]')).toHaveCount(0)
  await expect(page.locator('#approval-audit')).toContainText('Không có mục nào khớp bộ lọc.')
  expect(ed).toContain(`/workflows/${wid}`)
})
