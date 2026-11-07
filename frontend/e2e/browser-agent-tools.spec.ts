import { test, expect, type Page } from '@playwright/test'
import { login, N, newWorkflow } from './helpers'
import en from '../src/locales/en.json' with { type: 'json' }
import vi from '../src/locales/vi.json' with { type: 'json' }
import shipment from '../../examples/browser/lookup_shipment.json' with { type: 'json' }

async function jump(page: Page, node: string) {
  await expect(page.locator(`.react-flow__node[data-id="${node}"]`)).toHaveCount(1)
  await page.keyboard.press('ControlOrMeta+k')
  await page.locator('[data-testid=palette-item][data-id="node:' + node + '"]').click()
}
async function choose(page: Page, id: string, name: string) {
  await page.locator(`#${id}`).click(); await page.getByRole('option', { name, exact: true }).click()
}
async function connection(page: Page, headers: Record<string, string>, name: string) {
  const result = await (await page.request.post('/api/mcp/servers', { headers, data: { name, scope: 'user', transport: 'managed', adapter: 'browser', settings: { provider: 'local', allowed_origins: ['https://example.org'] }, secrets: {} } })).json()
  expect(result.success).toBe(true)
  return (await (await page.request.post(`/api/mcp/servers/${result.data.id}/discover`, { headers })).json()).data
}
const screenshot = async (page: Page, name: string, selector = '#config-panel') => {
  if (process.env.REVIEW_SHOTS) await page.locator(selector).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` })
}

for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`browser Agent URL bindings and recipe controls (${lang}, ${theme})`, async ({ page }) => {
    test.setTimeout(120_000)
    const headers = await login(page), t = lang === 'en' ? en : vi, suffix = `${lang}-${theme}`
    const server = await connection(page, headers, `Browser UI ${suffix}`)
    await page.setViewportSize({ width: 1440, height: 1100 })
    await page.evaluate(([language, mode]) => { localStorage.setItem('lang', language); localStorage.setItem('theme', mode); localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 240, right: 450, bottom: 400 })) }, [lang, theme])
    const tool = (operation: string) => ({ source: 'mcp', server_id: server.id, tool: operation, name: operation, description: operation, parameters: server.tools.find((item: { name: string }) => item.name === operation).input_schema })
    const graph = { name: `Browser Agent ${suffix}`, state: [{ name: 'message', type: 'string' }, { name: 'url', type: 'string' }, { name: 'answer', type: 'string' }],
      nodes: [N('start', 'start', 40), N('ag', 'agent', 320, { model: 'gpt-4o-mini', prompt: 'Use the URL from chat. Ask for the organisation when missing. Search only with a configured tool.', output_field: 'answer', max_rounds: 5, tools: [tool('navigate'), tool('fill')] }), N('end', 'end', 620)],
      edges: [{ id: 'a', source: 'start', target: 'ag' }, { id: 'b', source: 'ag', target: 'end' }] }
    const wid = await newWorkflow(page, headers, graph)
    await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="ag"]').click()
    await page.locator('#config-tab-settings').click()
    await expect(page.locator('#agent-tool-1-approval')).toBeDisabled()
    await expect(page.locator('#agent-tool-1-approval')).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('#human-approval')).toBeVisible()
    await expect(page.locator('#agent-auto')).toHaveCount(0)
    await expect(page.locator('#config-panel')).toContainText(t.browserTools.effectApproval)
    await page.locator('#config-tab-data').click()
    await expect(page.locator('#agent-tool-0-url-source')).toContainText(t.browserTools.sources.model)
    await expect(page.locator('#agent-tool-0-url-value')).toHaveCount(0)
    await choose(page, 'agent-tool-0-url-source', t.browserTools.sources.fixed)
    await page.locator('#agent-tool-0-url-value').fill('https://example.org/fixed')
    await choose(page, 'agent-tool-0-url-source', t.browserTools.sources.state)
    await page.locator('#agent-tool-0-url-value').fill('{{state.url}}')
    await choose(page, 'agent-tool-0-url-source', t.browserTools.sources.fixed)
    await expect(page.locator('#agent-tool-0-url-value')).toHaveValue('https://example.org/fixed')
    await choose(page, 'agent-tool-0-url-source', t.browserTools.sources.state)
    await expect(page.locator('#agent-tool-0-url-value .template-tag[data-field="url"]')).toBeVisible()
    await screenshot(page, `browser-agent-data-${suffix}`)
    await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
    const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data
    expect(saved.nodes.find((node: { id: string }) => node.id === 'ag').data.tools[0].url_binding).toEqual({ source: 'state', value: '{{state.url}}' })
    await page.locator('#config-tab-execution').click(); await expect(page.locator('#browser-execution')).toContainText(t.browserTools.executionHelp)
    await screenshot(page, `browser-agent-execution-${suffix}`)
    const recipe = structuredClone(shipment)
    recipe.name = `Recipe ${suffix}`; recipe.browser_recipe.connection_id = server.id
    for (const node of recipe.nodes) if (node.type === 'mcp') (node.data as Record<string, unknown>).server_id = server.id
    const rid = await newWorkflow(page, headers, recipe)
    await page.goto(`/workflows/${rid}`); await jump(page, 'start')
    await page.locator('#config-tab-settings').click()
    await expect(page.locator('#browser-recipe-enabled')).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('#browser-recipe-connection')).toContainText(server.name)
    await page.locator('#config-tab-data').click(); await expect(page.locator('#recipe-inputs-url')).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('#recipe-outputs-shipment')).toHaveAttribute('aria-checked', 'true')
    await screenshot(page, `browser-recipe-contract-${suffix}`)
    await jump(page, 'fill'); await page.locator('#config-tab-data').click()
    await expect(page.locator('#recipe-role')).toHaveValue('textbox')
    await page.locator('#recipe-target-text').fill('Order reference')
    await screenshot(page, `browser-recipe-target-${suffix}`)
    await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
    await page.reload(); await jump(page, 'fill'); await page.locator('#config-tab-data').click()
    await expect(page.locator('#recipe-target-text')).toHaveValue('Order reference')
    await page.setViewportSize({ width: 390, height: 844 }); await page.locator('#mobile-tab-config').click(); await page.locator('#config-tab-data').click()
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.locator('#recipe-role').focus(); await page.keyboard.press('Tab'); await expect(page.locator('#recipe-target-text')).toBeFocused()
    await screenshot(page, `browser-recipe-narrow-${suffix}`)
    await page.setViewportSize({ width: 1440, height: 1100 })
    const stored = (await (await page.request.get(`/api/workflows/${rid}`, { headers })).json()).data
    expect(stored.browser_recipe).toEqual(recipe.browser_recipe)
    await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="ag"]').click(); await page.locator('#config-tab-settings').click()
    await page.locator('#agent-add-tool').click(); await page.locator('#agent-add-workflow').click()
    await choose(page, 'agent-tool-2-workflow', recipe.name)
    await expect(page.locator('#agent-tool-2-in-url')).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('#agent-tool-2-out-shipment')).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('#agent-tool-2-in-url')).toBeDisabled()
    await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
    await page.goto(`/workflows/${rid}`); await jump(page, 'start'); await page.locator('#config-tab-settings').click()
    await page.locator('#browser-recipe-enabled').click(); await expect(page.locator('#confirm-delete-submit')).toBeDisabled()
    await page.locator('#confirm-delete-input').fill(recipe.name); await page.locator('#confirm-delete-submit').click()
    await expect(page.locator('#browser-recipe-enabled')).toHaveAttribute('aria-checked', 'false')
  })
}

test('web search/fetch grants use separate tools and fetch URL data binding', async ({ page }) => {
  const headers = await login(page)
  await page.evaluate(() => localStorage.setItem('lang', 'en'))
  const created = await (await page.request.post('/api/mcp/servers', { headers, data: { name: 'Web tool fixture', scope: 'user', transport: 'managed', adapter: 'web', settings: { enabled_tools: ['search', 'fetch'], search: { provider: 'searxng', endpoint: 'https://search.example.org/search' } }, secrets: {} } })).json()
  expect(created.success).toBe(true)
  const server = (await (await page.request.post(`/api/mcp/servers/${created.data.id}/discover`, { headers })).json()).data
  const graph = { name: 'Search first Agent', state: [{ name: 'message', type: 'string' }, { name: 'url', type: 'string' }, { name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 40), N('ag', 'agent', 320, { model: 'gpt-4o-mini', prompt: 'Ask which organisation/site when context is missing. Use configured search to discover candidates, then fetch a relevant public page.', output_field: 'answer', max_rounds: 5, tools: ['search', 'fetch'].map(operation => ({ source: 'mcp', name: operation, tool: operation, server_id: server.id, parameters: server.tools.find((item: { name: string }) => item.name === operation).input_schema })) }), N('end', 'end', 620)],
    edges: [{ id: 'a', source: 'start', target: 'ag' }, { id: 'b', source: 'ag', target: 'end' }] }
  const wid = await newWorkflow(page, headers, graph)
  await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="ag"]').click(); await page.locator('#config-tab-data').click()
  await expect(page.locator('#agent-tool-0-url-source')).toHaveCount(0)
  await choose(page, 'agent-tool-1-url-source', en.browserTools.sources.state)
  await page.locator('#agent-tool-1-url-value').fill('{{state.url}}')
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers })).json()).data
  expect(saved.nodes.find((node: { id: string }) => node.id === 'ag').data.tools[1].url_binding).toEqual({ source: 'state', value: '{{state.url}}' })
})

test('recipe lookup failure is shown and does not select an unusable workflow tool', async ({ page }) => {
  const headers = await login(page)
  await page.evaluate(() => localStorage.setItem('lang', 'en'))
  const server = await connection(page, headers, 'Lookup failure browser')
  const recipe = structuredClone(shipment); recipe.name = 'Unavailable recipe'; recipe.browser_recipe.connection_id = server.id
  for (const node of recipe.nodes) if (node.type === 'mcp') (node.data as Record<string, unknown>).server_id = server.id
  const rid = await newWorkflow(page, headers, recipe)
  const wid = await newWorkflow(page, headers, { name: 'Recipe lookup parent', state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
    nodes: [N('start', 'start', 40), N('ag', 'agent', 300, { model: 'gpt-4o-mini', prompt: 'Call a configured recipe.', output_field: 'answer', tools: [] }), N('end', 'end', 600)],
    edges: [{ id: 'a', source: 'start', target: 'ag' }, { id: 'b', source: 'ag', target: 'end' }] })
  await page.route(`**/api/workflows/${rid}`, route => route.fulfill({ status: 404, json: { success: false, error: { code: 'WORKFLOW_NOT_FOUND', message: 'Workflow not found' } } }))
  await page.goto(`/workflows/${wid}`); await page.locator('.react-flow__node[data-id="ag"]').click(); await page.locator('#config-tab-settings').click()
  await page.locator('#agent-add-tool').click(); await page.locator('#agent-add-workflow').click(); await choose(page, 'agent-tool-0-workflow', recipe.name)
  await expect(page.locator('#agent-tool-0').getByRole('alert')).toContainText(en.errors.WORKFLOW_NOT_FOUND)
  await expect(page.locator('#agent-tool-0-workflow-required')).toBeVisible()
})
