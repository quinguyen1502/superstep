import { test, expect, type Page } from '@playwright/test'
// TASK-0260: contextual handbook links in Settings → Channels (fixed published handbook, DEC-0086 option A).
const BASE = 'https://quinguyen1502.github.io/superstep/'

async function login(page: Page) {
  await page.goto('/login'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123'); await page.locator('#auth-submit').click()
  await expect(page).toHaveURL(/\/workflows$/)
}

test('channels: public URL missing and setup helpers link to the handbook in the UI language', async ({ page }) => {
  await login(page)
  // a studio without STUDIO_PUBLIC_URL and one personal Telegram connection (the e2e server sets the URL, so fake the read)
  await page.route(/\/api\/approvals\/channels(\?.*)?$/, async route => {
    if (route.request().method() !== 'GET') return route.continue()
    const res = await route.fetch(); const json = await res.json(); const body = json.data  // response envelope
    body.public_url = null
    body.channels = [{ id: 'hb-tg', kind: 'telegram', scope: 'user', name: 'Docs bot', team_id: null, hint: '••••abcd', created: 0, editable: false,
      callback_url: null, callback_path: '/api/approvals/callback/telegram/hb-tg', shared_callback_url: null, shared_callback_path: null, chat: null }]
    await route.fulfill({ response: res, json })
  })
  await page.goto('/settings/channels')
  const tg = page.locator('[data-testid=channel-card-telegram]')
  await expect(tg.locator('#ch-hb-tg-public-url-missing')).toContainText('Chưa đặt STUDIO_PUBLIC_URL')
  const help = tg.locator('#ch-hb-tg-public-url-help')
  await expect(help).toHaveText('Hướng dẫn')
  await expect(help).toHaveAttribute('href', `${BASE}vi/operate/expose-local/`)
  await expect(help).toHaveAttribute('target', '_blank'); await expect(help).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(help).toHaveAccessibleName(/mở studio cục bộ ra internet/)

  // add-connection helpers point at each platform's section
  for (const [kind, anchor] of [['slack', 'slack'], ['whatsapp', 'whatsapp-cloud-api']] as const) {
    const card = page.locator(`[data-testid=channel-card-${kind}]`)
    await card.locator(`#channel-card-${kind}-toggle`).click(); await card.locator(`#channel-card-${kind}-tab-user`).click()
    await expect(card.locator(`#add-${kind}-user-guide`)).toHaveAttribute('href', `${BASE}vi/operate/channels/#${anchor}`)
  }
  await tg.locator('#channel-card-telegram-tab-user').click()
  const open = tg.locator('#add-telegram-user-open'); if (await open.isVisible()) await open.click()
  await expect(tg.locator('#add-telegram-user-guide')).toHaveAttribute('href', `${BASE}vi/operate/channels/#telegram`)
  // the English site is covered by src/lib/__tests__/handbook.test.ts; switching the shared admin's language here would leak into parallel specs
})
