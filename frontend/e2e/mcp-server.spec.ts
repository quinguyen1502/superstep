import { test, expect, type Page } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { expectRowAligned } from './helpers/alignment'
// TASK-0114: expose a workflow as an MCP tool from the API dialog, copy the client config, and call /mcp with the token.
const shot = async (page: Page, name: string) => { if (process.env.REVIEW_SHOTS) await page.locator('#api-dialog').screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const rpc = (method: string, params: object = {}, id = 1) => ({ jsonrpc: '2.0', id, method, params })
const MCP_HEADERS = (token: string) => ({ Authorization: `Bearer ${token}`, Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18' })

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US', viewport: { width: 1280, height: 900 } })
  test(`mcp server: enable, client config, tools over /mcp (${lang})`, async ({ page }) => {
    const H = lang === 'vi' ? await login(page) : await (async () => {
      await page.goto('/login'); await page.getByLabel('Email').fill('admin@example.com'); await page.getByLabel('Password', { exact: true }).fill('admin123')
      await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
      return { Authorization: `Bearer ${(await (await page.request.post('/api/auth/login', { data: { email: 'admin@example.com', password: 'admin123' } })).json()).data.token}` }
    })()
    const wid = await newWorkflow(page, H, SIMPLE(`Mcp answer ${lang} ${Date.now() % 100000}`))
    await page.goto(`/workflows/${wid}`)
    await page.locator('#more-btn').click(); await page.locator('#api-btn').click()
    await page.locator('#api-token-name').fill('mcp'); await page.locator('#api-create').click()
    const token = await page.locator('#api-token-value').inputValue()
    await page.locator('#api-mcp-tab').click()
    const sw = page.locator('#mcp-enabled'); await expect(sw).toHaveAttribute('data-state', 'unchecked')
    const off = await page.request.post('/mcp', { headers: MCP_HEADERS(token), data: rpc('tools/list') })
    expect(off.status()).toBe(403); expect((await off.json()).error.code).toBe('MCP_SERVER_DISABLED')
    await sw.click(); await expect(sw).toHaveAttribute('data-state', 'checked')
    await expect(page.locator('#mcp-url')).toHaveValue(/\/mcp$/)
    await expect(page.locator('#mcp-snippet')).toContainText(token)  // the just-created token fills the snippet
    await expect(page.locator('#mcp-snippet')).toContainText('"url"')
    await expectRowAligned([page.locator('#mcp-url'), page.locator('#mcp-url + button')], { label: 'url + copy' })
    await shot(page, `feat-1-mcp-${lang}`)
    await page.locator('#mcp-client').click(); await page.getByRole('option', { name: 'Claude Desktop' }).click()
    await expect(page.locator('#mcp-snippet')).toContainText('mcp-remote')
    await shot(page, `feat-1-mcp-claude-${lang}`)
    // an MCP client's calls: initialize, tools/list, tools/call (stateless JSON responses)
    const init = await page.request.post('/mcp', { headers: MCP_HEADERS(token), data: rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'e2e', version: '1' } }) })
    expect(init.status()).toBe(200); expect((await init.json()).result.serverInfo.name).toBe('superstep')
    const tools = (await (await page.request.post('/mcp', { headers: MCP_HEADERS(token), data: rpc('tools/list', {}, 2) })).json()).result.tools
    expect(tools.map((t: { name: string }) => t.name).slice(1)).toEqual(['get_run', 'resume_run'])
    const call = (await (await page.request.post('/mcp', { headers: MCP_HEADERS(token), data: rpc('tools/call', { name: tools[0].name, arguments: { message: 'hi' } }, 3) })).json()).result
    expect(call.isError).toBe(false); expect(call.structuredContent.status).toBe('ok')
  })
})
