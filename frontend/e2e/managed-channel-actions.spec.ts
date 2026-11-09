import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { confirmDelete } from './confirm'
import { vt } from './catalog'

const WITH_EMAIL = process.env.E2E_CHANNEL_SMTP === '1'
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`managed channel actions reuse saved channels (${lang}, ${theme}, SMTP ${WITH_EMAIL ? 'on' : 'off'})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 })
    const headers = await login(page), suffix = `${lang}-${theme}`, port = process.env.E2E_CHAT_PORT || 8111
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    const values: Record<string, any> = {
      slack: { bot_token: `xoxb-1-T${lang}${theme}-fixture-token`, signing_secret: 'a'.repeat(32) },
      whatsapp: { access_token: 'fixture-whatsapp-token', phone_number_id: '1098765432', app_secret: 'a'.repeat(32), verify_token: 'fixture-verify-token' },
      email: {}, teams: { webhook_url: `http://127.0.0.1:${port}/teams/${suffix}` },
    }
    const fields: Record<string, Record<string, string>> = { slack: { destination_channel: 'C123TEST' }, whatsapp: { recipient_phone: '84901234567' }, email: { recipients: 'fixture-recipient@example.test' }, teams: {} }
    const labels: Record<string, string> = lang === 'en'
      ? { slack: 'Slack actions', whatsapp: 'WhatsApp actions', email: 'Email actions', teams: 'Microsoft Teams actions' }
      : { slack: 'Thao tác Slack', whatsapp: 'Thao tác WhatsApp', email: 'Thao tác email', teams: 'Thao tác Microsoft Teams' }
    // System SMTP is isolated behind an explicit flag; the normal suite's auth/notification setup stays unchanged.
    for (const kind of ['slack', 'whatsapp', ...(WITH_EMAIL ? ['email'] : []), 'teams']) {
      const channelName = `Fixture ${kind} ${suffix}`, name = `Managed ${kind} ${suffix}`
      const response = await page.request.post('/api/approvals/channels', { headers, data: { kind, name: channelName, ...values[kind] } })
      expect(response.ok(), await response.text()).toBeTruthy()
      const source = (await response.json()).data
      await page.goto('/settings/mcp'); await page.locator('#mcp-add').click()
      await page.locator('#mcp-new-name').fill(name); await page.locator('#mcp-new-transport').click()
      await page.getByRole('option', { name: lang === 'en' ? 'Managed connection' : vt('managedTools.transport'), exact: true }).click()
      await page.locator('#mcp-new-adapter').click(); await page.getByRole('option', { name: labels[kind], exact: true }).click()
      await page.locator('#mcp-new-channel_id').click(); await page.getByRole('option', { name: new RegExp(channelName) }).click()
      for (const [field, value] of Object.entries(fields[kind])) await page.locator(`#mcp-new-${field}`).fill(value)
      if (process.env.REVIEW_SHOTS) await page.locator('#mcp-new').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-${kind}-${suffix}.png` })
      await page.locator('#mcp-create').click()
      const card = page.locator('[data-testid^="mcp-card-"]', { hasText: name })
      await expect(card).toBeVisible(); await card.locator('[id$="-discover"]').click()
      const tool = kind === 'email' ? 'send_email' : 'send_message'
      await expect(card.getByTestId('mcp-tools')).toContainText(tool)
      const server = (await (await page.request.get('/api/mcp/servers', { headers })).json()).data.servers.find((s: any) => s.name === name)
      expect(server.settings.channel_id).toBe(source.id)
      const graph: any = SIMPLE(`Channel ${kind} ${suffix}`)
      graph.state.push({ name: 'result', type: 'object' })
      graph.nodes[1].type = 'mcp'; graph.nodes[1].data = { label: `Send ${kind}`, server_id: server.id, tool, arguments: { text: 'Synthetic acceptance message' }, output_field: 'result' }
      const wid = await newWorkflow(page, headers, graph)
      await page.goto(`/workflows/${wid}`); await page.locator('#run-btn').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
      await page.goto('/settings/mcp')
      const saved = page.locator(`[data-testid="mcp-card-${server.id}"]`)
      await expect(saved.getByTestId('managed-operations').locator('[data-outcome="confirmed"]')).toHaveCount(1)
      await saved.locator('[id$="-edit"]').click(); await saved.locator('[id$="-delete"]').click(); await confirmDelete(page, name)
      await expect(saved).toHaveCount(0)
    }
  })
}
