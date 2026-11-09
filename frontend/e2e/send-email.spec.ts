import { test, expect } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
import { vt, vtHead } from './catalog'
// an SMTP credential (form, preset, connection check) and a Send email node: a dry run without a credential,
// then a real send to the local SMTP sink started by playwright.config.ts.
const PORT = process.env.E2E_SMTP_PORT || '8125'
const WF = (name: string) => ({ name,
  state: [{ name: 'email', type: 'string' }, { name: 'name', type: 'string' }, { name: 'sent', type: 'object' }],
  nodes: [N('s', 'start', 40), N('mail', 'email', 300, { label: 'Notify', to: '{{state.email}}', subject: 'Hello {{state.name}}', body: 'Hi {{state.name}}', format: 'text', output_field: 'sent' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'mail' }, { id: '2', source: 'mail', target: 'e' }] })

test('send email: SMTP credential, dry run, then a real send', async ({ page }) => {
  const H = await login(page)
  const credName = `Mail ${Date.now()}`
  await page.locator('#creds-btn').click()
  await page.locator('#cred-name').fill(credName)
  await page.locator('#cred-provider').click(); await page.getByRole('option', { name: 'SMTP (email)' }).click()
  await expect(page.locator('#cred-base')).toHaveCount(0)
  await page.locator('#smtp-preset').click(); await page.getByRole('option', { name: 'Gmail' }).click()
  await expect(page.locator('#smtp-host')).toHaveValue('smtp.gmail.com'); await expect(page.locator('#smtp-preset-hint')).toBeVisible()
  await page.locator('#smtp-host').fill('127.0.0.1'); await expect(page.locator('#smtp-preset')).toContainText(vt('creds.smtp.presets.custom'))
  await page.locator('#smtp-port').fill(PORT)
  await page.locator('#smtp-security').click(); await page.getByRole('option', { name: vt('creds.smtp.securityOpts.none') }).click()
  await page.locator('#smtp-from').fill('studio@acme.test'); await page.locator('#smtp-from-name').fill('Acme')
  await page.locator('#cred-test').click()
  await expect(page.locator('#cred-test-result')).toContainText(vtHead('creds.smtp.testOk'))
  await page.locator('#cred-add').click()
  await expect(page.locator(`[data-cred="${credName}"] [data-smtp]`)).toHaveText(`studio@acme.test · 127.0.0.1:${PORT}`)
  await page.keyboard.press('Escape')

  const wid = await newWorkflow(page, H, WF(`Email ${Date.now()}`))
  const runs = async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: H })).json()).data
    .sort((a: { started: number }, b: { started: number }) => b.started - a.started)
  const run = async () => {
    await page.locator('#run-tab').click()
    await page.locator('#run-input').fill('{"email": "ann@example.com", "name": "Ann", "sent": {}}')
    await page.locator('#run-btn').click()
    await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
    return (await runs())[0].final_state.sent
  }
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="mail"]').click(); await page.locator('#config-tab-settings').click()
  await expect(page.locator('#email-settings')).toBeVisible(); await expect(page.locator('#email-dry-hint')).toBeVisible()
  const dry = await run()
  expect(dry).toMatchObject({ dry_run: true, sent: false, to: ['ann@example.com'], subject: 'Hello Ann', preview: 'Hi Ann' })

  await page.locator('.react-flow__node[data-id="mail"]').click(); await page.locator('#config-tab-settings').click()
  await page.locator('#email-credential').click(); await page.getByRole('option', { name: new RegExp(credName) }).click()
  await expect(page.locator('#email-dry-hint')).toHaveCount(0)
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const sent = await run()
  expect(sent).toMatchObject({ dry_run: false, sent: true, to: ['ann@example.com'], refused: [] })
  expect(sent.message_id).toMatch(/^<studio-[0-9a-f]+@acme\.test>$/)
})
