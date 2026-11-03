import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'

for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`managed HTTP API: configure, discover, execute and redact (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1350 })
    const headers = await login(page), suffix = `${lang}-${theme}`, name = `Internal API ${suffix}`
    await page.evaluate(([l, t]) => {
      localStorage.setItem('lang', l); localStorage.setItem('theme', t)
      localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 250, right: 320, bottom: 520 }))
    }, [lang, theme])
    await page.goto('/settings/mcp'); await page.locator('#mcp-add').click()
    await page.locator('#mcp-new-name').fill(name)
    await page.locator('#mcp-new-transport').click()
    await page.getByRole('option', { name: lang === 'en' ? 'Managed connection' : 'Kết nối được quản lý', exact: true }).click()
    await page.locator('#mcp-new-adapter').click()
    await page.getByRole('option', { name: lang === 'en' ? 'Generic HTTP API' : 'HTTP API tổng quát', exact: true }).click()
    await page.locator('#mcp-new-base_url').fill(`http://127.0.0.1:${process.env.E2E_CHAT_PORT || 8111}/generic`)
    await expect(page.locator('#mcp-new-tools_json')).toHaveValue(/create_record/)
    const tools = JSON.parse(await page.locator('#mcp-new-tools_json').inputValue())
    tools[0].response_schema = { type: 'object', required: ['ok'], properties: { ok: { const: true } } }
    await page.locator('#mcp-new-tools_json').fill(JSON.stringify(tools, null, 2))
    if (process.env.REVIEW_SHOTS) await page.locator('#mcp-new').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-http-${suffix}.png` })
    await page.locator('#mcp-new-headers').fill(JSON.stringify({ Authorization: 'Bearer fixture-http-key' }))
    await page.locator('#mcp-create').click()
    const card = page.locator('[data-testid^="mcp-card-"]', { hasText: name })
    await expect(card).toBeVisible(); await expect(card).not.toContainText('fixture-http-key')
    await card.locator('[id$="-discover"]').click(); await expect(card.getByTestId('mcp-tools')).toContainText('create_record')
    const server = (await (await page.request.get('/api/mcp/servers', { headers })).json()).data.servers.find((s: any) => s.name === name)
    const graph: any = SIMPLE(`HTTP acceptance ${suffix}`)
    graph.state.push({ name: 'result', type: 'object' })
    graph.nodes[1].type = 'mcp'; graph.nodes[1].data = { label: 'Create record', server_id: server.id, tool: 'create_record', arguments: { text: 'Synthetic acceptance data' }, output_field: 'result' }
    const wid = await newWorkflow(page, headers, graph)
    await page.goto(`/workflows/${wid}`); await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await page.locator('.trace-row[data-span="reply#1"]').click()
    await page.locator('#trace-detail').getByRole('tab', { name: 'Output', exact: true }).click()
    await expect(page.locator('#trace-detail')).toContainText('confirmed')
    await page.locator('#trace-detail button[aria-expanded="false"]').first().click()
    await expect(page.locator('#trace-detail')).toContainText('[redacted]')
    await expect(page.locator('#trace-detail')).not.toContainText('fixture-http-key')
    if (process.env.REVIEW_SHOTS) await page.locator('#trace-detail').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-http-result-${suffix}.png` })
    await page.goto('/settings/mcp')
    const edited = page.locator(`[data-testid="mcp-card-${server.id}"]`)
    await edited.locator('[id$="-edit"]').click()
    await expect(edited.locator('[id$="-tools_json"]')).toHaveValue(/response_schema/)
    await expect(edited.locator('[id$="-headers"]')).toHaveValue('')
  })
}
