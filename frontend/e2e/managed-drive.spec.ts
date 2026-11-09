import { test, expect } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
import { confirmDelete } from './confirm'
import { vt, vin } from './catalog'

test.skip(process.env.E2E_DRIVE_FIXTURE !== '1', 'Requires E2E_DRIVE_FIXTURE=1; all Google HTTP is isolated')
for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`Google Drive configure, create, read and inspect (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1150 })
    const headers = await login(page), suffix = `${lang}-${theme}`, name = `Drive ${suffix}`, folder = `fixture-folder-${suffix}`
    await page.evaluate(([l, t]) => {
      localStorage.setItem('lang', l); localStorage.setItem('theme', t)
      localStorage.setItem('lgs.editorPanels', JSON.stringify({ left: 250, right: 320, bottom: 520 }))
    }, [lang, theme])
    await page.goto('/settings/mcp'); await page.locator('#mcp-add').click()
    await page.locator('#mcp-new-name').fill(name); await page.locator('#mcp-new-transport').click()
    await page.getByRole('option', { name: lang === 'en' ? 'Managed connection' : vt('managedTools.transport'), exact: true }).click()
    await page.locator('#mcp-new-adapter').click()
    await page.getByRole('option', { name: lang === 'en' ? 'Google Drive files' : vt('managedTools.adapters.google_drive'), exact: true }).click()
    await page.locator('#mcp-new-folder_id').fill(folder)
    if (process.env.REVIEW_SHOTS) await page.locator('#mcp-new').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-drive-${suffix}.png` })
    await page.locator('#mcp-new-google_credentials').fill(JSON.stringify({ type: 'authorized_user', client_id: 'fixture.apps.googleusercontent.com', client_secret: 'fixture-client-secret', refresh_token: 'fixture-refresh-token' }))
    await page.locator('#mcp-create').click()
    const card = page.locator('[data-testid^="mcp-card-"]', { hasText: name })
    await expect(card).toBeVisible(); await expect(card).not.toContainText('fixture-refresh-token')
    await card.locator('[id$="-discover"]').click()
    for (const tool of ['list_files', 'get_file', 'read_text_file', 'create_text_file']) await expect(card.getByTestId('mcp-tools')).toContainText(tool)
    const server = (await (await page.request.get('/api/mcp/servers', { headers })).json()).data.servers.find((s: any) => s.name === name)
    const beforeUploads = (await (await page.request.get('/api/_drive-fixture')).json()).data.uploads
    const content = `${vin('drive.expense')}: 50.000 VND\n`
    const graph = { name: `Drive acceptance ${suffix}`, state: [{ name: 'created', type: 'object' }, { name: 'text', type: 'object' }, { name: 'files', type: 'object' }], nodes: [
      N('start', 'start', 20), N('create', 'mcp', 250, { label: 'Create receipt', server_id: server.id, tool: 'create_text_file', arguments: { name: 'receipt.txt', content }, output_field: 'created' }),
      N('read', 'mcp', 500, { label: 'Read receipt', server_id: server.id, tool: 'read_text_file', arguments: { file_id: '{{state.created.file.id}}' }, output_field: 'text' }),
      N('list', 'mcp', 750, { label: 'List folder', server_id: server.id, tool: 'list_files', arguments: { page_size: 10 }, output_field: 'files' }), N('end', 'end', 1000),
    ], edges: [['start', 'create'], ['create', 'read'], ['read', 'list'], ['list', 'end']].map(([source, target]) => ({ id: `${source}-${target}`, source, target })) }
    const wid = await newWorkflow(page, headers, graph)
    await page.goto(`/workflows/${wid}`); await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await page.locator('.trace-row[data-span="create#1"]').click()
    await page.locator('#trace-detail').getByRole('tab', { name: 'Output', exact: true }).click()
    await expect(page.locator('#trace-detail')).toContainText('confirmed')
    await page.locator('#trace-detail button[aria-expanded="false"]').first().click()
    await expect(page.locator('#trace-detail')).toContainText('receipt.txt')
    if (process.env.REVIEW_SHOTS) await page.locator('#trace-detail').screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-drive-created-${suffix}.png` })
    await page.locator('.trace-row[data-span="read#1"]').click()
    await expect(page.locator('#trace-detail')).toContainText(vin('drive.expense'))
    await expect(page.locator('#trace-detail')).not.toContainText('fixture-client-secret')
    const recorded = (await (await page.request.get('/api/_drive-fixture')).json()).data
    expect(recorded.uploads).toBe(beforeUploads + 1)
    expect(recorded.files.some((file: any) => file.name === 'receipt.txt')).toBeTruthy()
    await page.goto('/settings/mcp')
    const saved = page.locator(`[data-testid="mcp-card-${server.id}"]`)
    await expect(saved.getByTestId('managed-operations').locator('[data-outcome="confirmed"]')).toHaveCount(3)

    // A real lost response in the local Google HTTP double, then read-only recovery in the UI.
    await page.request.post('/api/_drive-fixture/lose-ack')
    try {
      const uncertain = structuredClone(graph)
      uncertain.name = `Drive lost acknowledgement ${suffix}`
      const uncertainId = await newWorkflow(page, headers, uncertain)
      await page.goto(`/workflows/${uncertainId}`); await page.locator('#run-btn').click()
      await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'error', { timeout: 20_000 })
      await page.goto('/settings/mcp')
      const operations = saved.getByTestId('managed-operations')
      const unknown = operations.locator('[data-outcome="unknown"]')
      await expect(unknown).toHaveCount(1)
      if (process.env.REVIEW_SHOTS) await unknown.screenshot({ path: `${process.env.REVIEW_SHOTS}/managed-drive-unknown-${suffix}.png` })
      await unknown.getByRole('button', { name: lang === 'en' ? 'Check external result' : vt('managedTools.reconcile'), exact: true }).click()
      await expect(operations.locator('[data-outcome="unknown"]')).toHaveCount(0)
      await expect(operations.locator('[data-outcome="confirmed"]')).toHaveCount(4)
      const recovered = (await (await page.request.get('/api/_drive-fixture')).json()).data
      expect(recovered.uploads).toBe(beforeUploads + 2) // one per run; recovery did not upload
    } finally { await page.request.post('/api/_drive-fixture/restore') }

    await saved.locator('[id$="-edit"]').click()
    await expect(saved.locator('[id$="-google_credentials"]')).toHaveValue('')
    await expect(saved.locator('[id$="-folder_id"]')).toHaveValue(folder)
    await saved.locator('[id$="-delete"]').click(); await confirmDelete(page, name); await expect(saved).toHaveCount(0)
  })
}
