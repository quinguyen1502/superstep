import { test, expect, type Page } from '@playwright/test'
import { login, N, newWorkflow } from './helpers'
// TASK-0081: TypeScript in Tool node Code mode. An admin picks "Code (TypeScript)" in the Mode select (the untouched Python
// starter becomes the TypeScript one), sees the generated State type, tests and runs the code; the canvas shows "TS";
// the admin card lists both languages. Needs a server that can run TypeScript (Deno on the host with
// E2E_CODE_RUNTIME=subprocess, or Docker with studio-code-ts:1); skips otherwise.
const SHOUT = 'export function main(state: State) {\n  console.log("got", state.message)\n  return (state.message ?? "").toUpperCase()\n}\n'
const WF = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'count', type: 'integer' }, { name: 'out', type: 'string' }],
  nodes: [N('s', 'start', 40), N('c', 'tool', 300, { label: 'Shout', mode: 'function', function: 'lookup_order', output_field: 'out' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'c' }, { id: '2', source: 'c', target: 'e' }] })

async function setCode(page: Page, code: string) {
  await page.locator('#code-source').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText(code)
}

test('code mode in TypeScript: switch language, State type, test, run, admin card', async ({ page }) => {
  const H = await login(page)
  const rt = (await (await page.request.get('/api/meta/runtime', { headers: H })).json()).data
  const ts = (rt.languages || []).find((l: { id: string }) => l.id === 'typescript')
  test.skip(!rt.available || !ts?.available, `TypeScript cannot run here: ${ts?.problem || rt.problem || rt.code_runtime}`)
  const wid = await newWorkflow(page, H, WF(`TS ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="c"]').click(); await page.locator('#config-tab-settings').click()
  await page.locator('#tool-mode').click(); await page.getByRole('option', { name: /^Code \(Python/ }).click()
  await expect(page.locator('#code-source')).toContainText('def main(state)')

  // one Mode option per available language, each with the "Runs on host" badge in subprocess mode
  await page.locator('#tool-mode').click()
  await expect(page.locator('#tool-mode-code-python [data-testid="mode-unisolated"]')).toHaveText('Chạy trực tiếp trên server')
  await page.locator('#tool-mode-code-typescript').click()
  await expect(page.locator('#tool-mode')).toContainText('Code (TypeScript)')
  await expect(page.locator('#code-language')).toHaveCount(0)  // no separate language picker
  await expect(page.locator('#code-source')).toContainText('export function main(state: State)')  // starter swapped
  await expect(page.locator('#code-source')).toHaveAttribute('data-language', 'typescript')
  await expect(page.locator('#code-language-kept')).toHaveCount(0)
  await expect(page.locator('#code-state-type')).toContainText('message?: string')
  await expect(page.locator('#code-state-type')).toContainText('count?: number')
  await expect(page.locator('.react-flow__node[data-id="c"] [data-testid="node-language"]')).toHaveText('TS')

  await setCode(page, SHOUT)
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill('{"message": "xin chào"}')
  await page.locator('.react-flow__node[data-id="c"]').click()
  await page.locator('#code-test').click()
  await expect(page.locator('#code-test-result')).toContainText('XIN CHÀO', { timeout: 30_000 })
  await expect(page.locator('#code-test-result [data-testid="code-stdout"]')).toHaveText('got xin chào')
  // the config panel never scrolls sideways (long Select labels / State type / editor lines must not widen it)
  const overflow = await page.locator('#config-panel [data-slot="scroll-area-viewport"]').evaluate(e => ({ sw: e.scrollWidth, cw: e.clientWidth }))
  expect(overflow.sw).toBeLessThanOrEqual(overflow.cw)

  // edited code is kept when switching back, with a hint
  await page.locator('#tool-mode').click(); await page.locator('#tool-mode-code-python').click()
  await expect(page.locator('#code-language-kept')).toBeVisible()
  await expect(page.locator('#code-source')).toContainText('export function main')
  await page.locator('#tool-mode').click(); await page.locator('#tool-mode-code-typescript').click()

  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
  expect(saved.nodes.find((n: { id: string }) => n.id === 'c').data.language).toBe('typescript')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })

  await page.goto('/settings/users')
  await expect(page.locator('#code-language-row-typescript [data-testid="code-language-status"]')).toHaveText('Sẵn sàng')
  await expect(page.locator('#code-language-row-python')).toBeVisible()
})
